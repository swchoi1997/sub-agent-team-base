"""테스트용 가짜 사내 LLM (Anthropic Messages API 흉내).

키마다 하루 토큰 한도가 있고, 다 쓰면 429를 낸다.
단독 실행: MOCK_KEYS="key-a:300,key-b:300" uvicorn tests.mock_upstream:app --port 9900
"""

from __future__ import annotations

import json
import os

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route


class MockLLM:
    def __init__(self, limits: dict[str, int], output_tokens: int = 5, rate_limited: dict[str, int] | None = None):
        self.limits = dict(limits)
        self.used = {k: 0 for k in limits}
        self.output_tokens = output_tokens
        self.rate_limited = dict(rate_limited or {})  # key -> retry-after 초 (일시 제한 흉내)
        self.calls: list[str] = []  # 요청에 쓰인 키 순서
        self.seen_headers: list[dict] = []

    def _key(self, request: Request) -> str | None:
        if "x-api-key" in request.headers:
            return request.headers["x-api-key"]
        auth = request.headers.get("authorization", "")
        return auth[7:] if auth.lower().startswith("bearer ") else None

    async def messages(self, request: Request) -> Response:
        key = self._key(request)
        self.seen_headers.append(dict(request.headers))
        if key not in self.limits:
            return JSONResponse(
                {"type": "error", "error": {"type": "authentication_error", "message": "invalid x-api-key"}},
                status_code=401,
            )
        self.calls.append(key)
        if key in self.rate_limited:
            retry = self.rate_limited.pop(key)
            return JSONResponse(
                {"type": "error", "error": {"type": "rate_limit_error", "message": "slow down"}},
                status_code=429,
                headers={"retry-after": str(retry)},
            )
        if self.used[key] >= self.limits[key]:
            return JSONResponse(
                {"type": "error", "error": {"type": "rate_limit_error", "message": "daily quota exceeded"}},
                status_code=429,
            )
        raw = await request.body()
        payload = json.loads(raw or b"{}")
        in_tokens = max(1, len(raw) // 4)
        out_tokens = self.output_tokens
        self.used[key] += in_tokens + out_tokens
        model = payload.get("model", "mock-model")
        text = f"hello from {key}"

        if payload.get("stream"):
            return StreamingResponse(self._sse(model, text, in_tokens, out_tokens), media_type="text/event-stream")
        return JSONResponse(
            {
                "id": "msg_mock",
                "type": "message",
                "role": "assistant",
                "model": model,
                "content": [{"type": "text", "text": text}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": in_tokens, "output_tokens": out_tokens},
            }
        )

    async def _sse(self, model: str, text: str, in_tokens: int, out_tokens: int):
        def ev(name: str, data: dict) -> bytes:
            return f"event: {name}\ndata: {json.dumps(data)}\n\n".encode()

        yield ev(
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_mock",
                    "type": "message",
                    "role": "assistant",
                    "model": model,
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": in_tokens, "output_tokens": 1},
                },
            },
        )
        yield ev(
            "content_block_start",
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        )
        yield ev(
            "content_block_delta",
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text}},
        )
        yield ev("content_block_stop", {"type": "content_block_stop", "index": 0})
        yield ev(
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"output_tokens": out_tokens},
            },
        )
        yield ev("message_stop", {"type": "message_stop"})

    async def count_tokens(self, request: Request) -> Response:
        raw = await request.body()
        return JSONResponse({"input_tokens": max(1, len(raw) // 4)})

    def app(self) -> Starlette:
        return Starlette(
            routes=[
                Route("/v1/messages", self.messages, methods=["POST"]),
                Route("/v1/messages/count_tokens", self.count_tokens, methods=["POST"]),
            ]
        )


def _limits_from_env() -> dict[str, int]:
    spec = os.environ.get("MOCK_KEYS", "key-a:300,key-b:300,key-c:300")
    return {k: int(v) for k, v in (item.split(":") for item in spec.split(",") if item)}


mock = MockLLM(_limits_from_env())
app = mock.app()
