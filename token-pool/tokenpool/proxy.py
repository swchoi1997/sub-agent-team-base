"""로컬 프록시: Claude Code 요청에 풀에서 고른 실제 키를 넣어 사내 LLM으로 전달한다."""

from __future__ import annotations

import datetime as dt
import json
import logging
from contextlib import asynccontextmanager
from typing import Callable
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from .config import Config
from .crypto import KeyCipher
from .db import Store, utcnow
from .selector import KeyInfo, rank

log = logging.getLogger("tokenpool")

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "proxy-connection",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
# 들어온 인증 헤더(Claude Code의 더미 키)는 버리고 풀의 키로 바꾼다.
# 사용량을 읽어야 하므로 업스트림에는 압축 없는 응답을 요청한다.
STRIP_REQUEST = HOP_BY_HOP | {"host", "content-length", "x-api-key", "authorization", "accept-encoding"}
STRIP_RESPONSE = HOP_BY_HOP | {"content-length", "content-encoding"}


def anthropic_error(status: int, message: str, kind: str = "rate_limit_error") -> JSONResponse:
    return JSONResponse({"type": "error", "error": {"type": kind, "message": message}}, status_code=status)


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None  # HTTP-date 형식은 일일 한도로 취급


class UsageTracker:
    """응답 본문(JSON 또는 SSE)에서 Anthropic usage를 뽑아낸다."""

    def __init__(self, content_type: str):
        self.is_sse = "text/event-stream" in content_type
        self._buf = b""
        self.in_tokens = 0
        self.out_tokens = 0
        self.model: str | None = None

    @staticmethod
    def _input_tokens(usage: dict) -> int:
        return sum(
            int(usage.get(k) or 0)
            for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
        )

    def _apply_usage(self, usage: dict | None, *, cumulative_out: bool) -> None:
        if not isinstance(usage, dict):
            return
        self.in_tokens = max(self.in_tokens, self._input_tokens(usage))
        out = int(usage.get("output_tokens") or 0)
        self.out_tokens = max(self.out_tokens, out) if cumulative_out else out

    def feed(self, chunk: bytes) -> None:
        self._buf += chunk
        if not self.is_sse:
            return
        *lines, self._buf = self._buf.split(b"\n")
        for line in lines:
            self._handle_sse_line(line.strip())

    def _handle_sse_line(self, line: bytes) -> None:
        if not line.startswith(b"data:"):
            return
        try:
            event = json.loads(line[5:].strip())
        except ValueError:
            return
        if not isinstance(event, dict):
            return
        if event.get("type") == "message_start":
            message = event.get("message") or {}
            self.model = message.get("model") or self.model
            self._apply_usage(message.get("usage"), cumulative_out=True)
        elif event.get("type") == "message_delta":
            # message_delta의 output_tokens는 누적값
            self._apply_usage(event.get("usage"), cumulative_out=True)

    def finish(self) -> None:
        if self.is_sse:
            if self._buf.strip():
                self._handle_sse_line(self._buf.strip())
            return
        try:
            body = json.loads(self._buf or b"{}")
        except ValueError:
            return
        if isinstance(body, dict):
            self.model = body.get("model") or self.model
            self._apply_usage(body.get("usage"), cumulative_out=False)


class TokenPoolProxy:
    def __init__(
        self,
        cfg: Config,
        store: Store,
        cipher: KeyCipher,
        client: httpx.AsyncClient | None = None,
        now: Callable[[], dt.datetime] = utcnow,
    ):
        self.cfg = cfg
        self.store = store
        self.cipher = cipher
        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=600.0, write=60.0, pool=10.0)
        )
        self.now = now
        self.tz = ZoneInfo(cfg.timezone)
        self.upstream = cfg.upstream.rstrip("/")
        self.me_id: int | None = None
        self.sticky_id: int | None = None

    def today(self) -> dt.date:
        return self.now().replace(tzinfo=dt.timezone.utc).astimezone(self.tz).date()

    def _auth_headers(self, api_key: str) -> dict[str, str]:
        if self.cfg.auth_header.lower() == "authorization":
            return {"authorization": f"Bearer {api_key}"}
        return {self.cfg.auth_header: api_key}

    async def _me(self) -> int | None:
        if self.me_id is None:
            self.me_id = await run_in_threadpool(self.store.member_id, self.cfg.me)
        return self.me_id

    async def health(self, request: Request) -> Response:
        return JSONResponse({"ok": True, "me": self.cfg.me, "upstream": self.upstream})

    async def handle(self, request: Request) -> Response:
        body = await request.body()
        url = self.upstream + request.url.path
        if request.url.query:
            url += "?" + request.url.query
        base_headers = {k: v for k, v in request.headers.items() if k.lower() not in STRIP_REQUEST}
        base_headers["accept-encoding"] = "identity"

        day = self.today()
        me_id = await self._me()
        tried: set[int] = set()

        for _ in range(self.cfg.max_attempts):
            snap = await run_in_threadpool(self.store.snapshot, day)
            candidates = [
                k for k in rank(snap, me_id, self.now(), self.cfg.borrow_ratio, self.sticky_id) if k.id not in tried
            ]
            if not candidates:
                break
            key = candidates[0]
            tried.add(key.id)
            try:
                api_key = self.cipher.decrypt(key.api_key_enc)
            except ValueError as exc:
                log.error("%s 키 복호화 실패: %s", key.name, exc)
                continue

            upstream_req = self.client.build_request(
                request.method, url, content=body, headers={**base_headers, **self._auth_headers(api_key)}
            )
            try:
                resp = await self.client.send(upstream_req, stream=True)
            except httpx.HTTPError as exc:
                # 네트워크 문제는 키 탓이 아니므로 키를 막지 않고 그대로 실패시킨다
                log.error("업스트림 연결 실패: %s", exc)
                return anthropic_error(502, f"tokenpool: 사내 LLM 연결 실패 ({exc.__class__.__name__})", "api_error")

            if resp.status_code == 429:
                await resp.aread()
                await resp.aclose()
                await self._on_rate_limited(key, day, parse_retry_after(resp.headers.get("retry-after")))
                continue
            if resp.status_code == 401:
                await resp.aread()
                await resp.aclose()
                log.warning("%s 키 인증 실패(401) → 오늘 풀에서 제외", key.name)
                await run_in_threadpool(self.store.mark_blocked, key.id, day, "auth")
                await run_in_threadpool(self.store.record_usage, key.id, day, 0, 0, self.cfg.me, None, 401)
                continue

            self.sticky_id = key.id
            return self._relay(resp, key, day)

        return anthropic_error(
            429, "tokenpool: 사용할 수 있는 키가 없습니다. 팀 풀의 모든 키가 오늘 한도를 소진했거나 쉬는 중입니다."
        )

    async def _on_rate_limited(self, key: KeyInfo, day: dt.date, retry_after: float | None) -> None:
        if retry_after is not None and retry_after <= self.cfg.short_cooldown_max:
            until = self.now() + dt.timedelta(seconds=retry_after)
            log.info("%s 키 일시 제한 → %ss 쿨다운", key.name, int(retry_after))
            await run_in_threadpool(self.store.set_cooldown, key.id, until)
        else:
            log.info("%s 키 오늘 한도 소진 → 다음 키로 전환", key.name)
            await run_in_threadpool(self.store.mark_blocked, key.id, day, "quota")
        await run_in_threadpool(self.store.record_usage, key.id, day, 0, 0, self.cfg.me, None, 429)

    def _relay(self, resp: httpx.Response, key: KeyInfo, day: dt.date) -> StreamingResponse:
        tracker = UsageTracker(resp.headers.get("content-type", ""))
        headers = {k: v for k, v in resp.headers.items() if k.lower() not in STRIP_RESPONSE}
        headers["x-tokenpool-key-owner"] = quote(key.name)  # 한글 이름은 퍼센트 인코딩

        async def body():
            try:
                async for chunk in resp.aiter_raw():
                    tracker.feed(chunk)
                    yield chunk
            finally:
                await resp.aclose()
                tracker.finish()
                try:
                    await run_in_threadpool(
                        self.store.record_usage,
                        key.id,
                        day,
                        tracker.in_tokens,
                        tracker.out_tokens,
                        self.cfg.me,
                        tracker.model,
                        resp.status_code,
                    )
                except Exception:  # 기록 실패가 응답을 깨면 안 됨
                    log.exception("사용량 기록 실패")

        return StreamingResponse(body(), status_code=resp.status_code, headers=headers)


def create_app(proxy: TokenPoolProxy) -> Starlette:
    @asynccontextmanager
    async def lifespan(app):
        yield
        await proxy.client.aclose()

    methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
    return Starlette(
        routes=[
            Route("/_tokenpool/health", proxy.health, methods=["GET"]),
            Route("/{path:path}", proxy.handle, methods=methods),
        ],
        lifespan=lifespan,
    )
