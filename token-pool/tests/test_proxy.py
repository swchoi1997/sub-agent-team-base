import datetime as dt
import json

import httpx
import pytest

from tokenpool.config import Config
from tokenpool.crypto import KeyCipher, generate_secret
from tokenpool.db import Store
from tokenpool.proxy import TokenPoolProxy, UsageTracker, create_app

from .mock_upstream import MockLLM

# 2026-11-18 03:00 UTC = 12:00 KST
NOW = dt.datetime(2026, 11, 18, 3, 0)
DAY = dt.date(2026, 11, 18)
REQ = {"model": "internal-model", "max_tokens": 50, "messages": [{"role": "user", "content": "hi"}]}


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def anyio_backend():
    return "asyncio"


def make_env(tmp_path, limits, me="me", members=None, rate_limited=None, auth_header="x-api-key"):
    """members: {이름: 키}. 기본은 me/kim/lee 3명."""
    members = members or {"me": "key-me", "kim": "key-kim", "lee": "key-lee"}
    cipher = KeyCipher(generate_secret())
    store = Store(f"sqlite:///{tmp_path / 'pool.db'}")
    store.create_all()
    for name, key in members.items():
        store.upsert_member(name, cipher.encrypt(key))
    mock = MockLLM(limits, rate_limited=rate_limited)
    upstream = httpx.AsyncClient(transport=httpx.ASGITransport(app=mock.app()), base_url="http://llm")
    cfg = Config(me=me, db_url="unused", upstream="http://llm", auth_header=auth_header)
    clock = Clock(NOW)
    proxy = TokenPoolProxy(cfg, store, cipher, client=upstream, now=clock)
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(proxy)), base_url="http://proxy")
    return client, mock, store, clock


async def post(client, body=REQ):
    return await client.post(
        "/v1/messages", json=body, headers={"x-api-key": "tokenpool-local", "anthropic-version": "2023-06-01"}
    )


@pytest.mark.anyio
async def test_uses_own_key_and_replaces_dummy_auth(tmp_path):
    client, mock, store, _ = make_env(tmp_path, {"key-me": 10_000, "key-kim": 10_000, "key-lee": 10_000})
    r = await post(client)
    assert r.status_code == 200
    assert r.json()["content"][0]["text"] == "hello from key-me"
    assert r.headers["x-tokenpool-key-owner"] == "me"
    assert mock.seen_headers[0]["x-api-key"] == "key-me"
    assert mock.seen_headers[0]["anthropic-version"] == "2023-06-01"
    me_id = store.member_id("me")
    snap = store.snapshot(DAY)
    assert snap.daily[me_id].used_out == 5 and snap.daily[me_id].used_in > 0


@pytest.mark.anyio
async def test_switches_to_leave_member_when_own_quota_exhausted(tmp_path):
    client, mock, store, _ = make_env(tmp_path, {"key-me": 1, "key-kim": 10_000, "key-lee": 10_000})
    store.add_leave("lee", [DAY])
    assert (await post(client)).status_code == 200  # 내 키로 한 번 성공 → 한도 넘김
    r = await post(client)  # 내 키 429 → 연차인 lee 키로
    assert r.status_code == 200
    assert r.json()["content"][0]["text"] == "hello from key-lee"
    assert mock.calls == ["key-me", "key-me", "key-lee"]

    snap = store.snapshot(DAY)
    assert snap.daily[store.member_id("me")].blocked_reason == "quota"
    # 소진된 내 키는 같은 날 다시 시도하지 않음
    await post(client)
    assert mock.calls[-1] == "key-lee"
    assert store.borrowings(DAY)[0][:2] == ("lee", "me")


@pytest.mark.anyio
async def test_streaming_usage_is_tracked_and_relayed(tmp_path):
    client, mock, store, _ = make_env(tmp_path, {"key-me": 10_000, "key-kim": 1, "key-lee": 1})
    async with client.stream(
        "POST", "/v1/messages", json={**REQ, "stream": True}, headers={"x-api-key": "dummy"}
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = b"".join([c async for c in r.aiter_raw()])
    assert b"message_stop" in body and b"hello from key-me" in body
    state = store.snapshot(DAY).daily[store.member_id("me")]
    assert state.used_out == 5 and state.used_in > 1


@pytest.mark.anyio
async def test_all_keys_exhausted_returns_pool_error(tmp_path):
    client, mock, store, _ = make_env(tmp_path, {"key-me": 0, "key-kim": 0, "key-lee": 0})
    r = await post(client)
    assert r.status_code == 429
    assert r.json()["error"]["type"] == "rate_limit_error"
    assert "tokenpool" in r.json()["error"]["message"]
    assert sorted(mock.calls) == ["key-kim", "key-lee", "key-me"]


@pytest.mark.anyio
async def test_short_retry_after_is_cooldown_not_daily_block(tmp_path):
    client, mock, store, clock = make_env(
        tmp_path, {"key-me": 10_000, "key-kim": 10_000, "key-lee": 10_000}, rate_limited={"key-me": 30}
    )
    r = await post(client)
    assert r.status_code == 200 and r.headers["x-tokenpool-key-owner"] in ("kim", "lee")
    me_id = store.member_id("me")
    assert store.snapshot(DAY).daily[me_id].blocked_reason is None
    clock.t = NOW + dt.timedelta(seconds=31)  # 쿨다운 끝나면 다시 내 키
    r = await post(client)
    assert r.headers["x-tokenpool-key-owner"] == "me"


@pytest.mark.anyio
async def test_invalid_key_is_skipped_for_the_day(tmp_path):
    client, mock, store, _ = make_env(
        tmp_path,
        {"key-kim": 10_000, "key-lee": 10_000},
        members={"me": "revoked-key", "kim": "key-kim", "lee": "key-lee"},
    )
    r = await post(client)
    assert r.status_code == 200
    assert store.snapshot(DAY).daily[store.member_id("me")].blocked_reason == "auth"


@pytest.mark.anyio
async def test_upstream_client_errors_pass_through_without_switching(tmp_path):
    client, mock, store, _ = make_env(tmp_path, {"key-me": 10_000, "key-kim": 10_000, "key-lee": 10_000})
    r = await client.get("/v1/unknown", headers={"x-api-key": "dummy"})
    assert r.status_code == 404
    assert store.snapshot(DAY).daily[store.member_id("me")].blocked_reason is None


@pytest.mark.anyio
async def test_bearer_auth_header_mode(tmp_path):
    client, mock, store, _ = make_env(
        tmp_path, {"key-me": 10_000, "key-kim": 1, "key-lee": 1}, auth_header="authorization"
    )
    r = await client.post("/v1/messages", json=REQ, headers={"authorization": "Bearer tokenpool-local"})
    assert r.status_code == 200
    assert mock.seen_headers[0]["authorization"] == "Bearer key-me"
    assert "x-api-key" not in mock.seen_headers[0]


@pytest.mark.anyio
async def test_day_rollover_uses_kst_midnight(tmp_path):
    client, mock, store, clock = make_env(tmp_path, {"key-me": 1, "key-kim": 10_000, "key-lee": 10_000})
    await post(client)
    await post(client)  # 내 키 소진
    clock.t = dt.datetime(2026, 11, 18, 15, 0)  # 2026-11-19 00:00 KST
    mock.used["key-me"] = 0  # 업스트림도 자정에 리셋
    r = await post(client)
    assert r.headers["x-tokenpool-key-owner"] == "me"


def test_usage_tracker_sse_split_across_chunks():
    t = UsageTracker("text/event-stream")
    events = (
        b'event: message_start\ndata: {"type":"message_start","message":{"model":"m","usage":'
        b'{"input_tokens":7,"cache_read_input_tokens":3,"output_tokens":1}}}\n\n'
        b'event: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":42}}\n\n'
    )
    for i in range(0, len(events), 9):
        t.feed(events[i : i + 9])
    t.finish()
    assert (t.in_tokens, t.out_tokens, t.model) == (10, 42, "m")


def test_usage_tracker_json():
    t = UsageTracker("application/json")
    t.feed(json.dumps({"model": "m", "usage": {"input_tokens": 4, "output_tokens": 6}}).encode())
    t.finish()
    assert (t.in_tokens, t.out_tokens) == (4, 6)
