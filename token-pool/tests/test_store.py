import datetime as dt
from concurrent.futures import ThreadPoolExecutor

import pytest

from tokenpool.db import Store

DAY = dt.date(2026, 11, 18)


@pytest.fixture
def store(tmp_path):
    s = Store(f"sqlite:///{tmp_path / 'pool.db'}")
    s.create_all()
    return s


def test_usage_accumulates_atomically_across_threads(store):
    mid = store.upsert_member("kim", "enc")

    def hit(_):
        store.record_usage(mid, DAY, 10, 5, "lee", "m", 200)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(hit, range(40)))

    snap = store.snapshot(DAY)
    assert snap.daily[mid].used == 40 * 15
    assert snap.daily[mid].requests == 40


def test_quota_block_learns_limit_and_resets_next_day(store):
    mid = store.upsert_member("kim", "enc")
    store.record_usage(mid, DAY, 700, 300, "kim", "m", 200)
    store.mark_blocked(mid, DAY, "quota")

    today = store.snapshot(DAY)
    assert today.daily[mid].blocked_reason == "quota"
    assert today.members[0].learned_limit == 1000

    tomorrow = store.snapshot(DAY + dt.timedelta(days=1))
    assert mid not in tomorrow.daily  # 날짜 단위라 자정 지나면 자동 초기화
    assert tomorrow.members[0].learned_limit == 1000  # 학습한 한도는 유지


def test_auth_block_does_not_learn_limit(store):
    mid = store.upsert_member("kim", "enc")
    store.record_usage(mid, DAY, 50, 0, "kim", "m", 200)
    store.mark_blocked(mid, DAY, "auth")
    assert store.snapshot(DAY).members[0].learned_limit is None


def test_leave_and_disable_and_unblock(store):
    a = store.upsert_member("kim", "enc")
    store.upsert_member("lee", "enc")
    store.add_leave("kim", [DAY, DAY + dt.timedelta(days=1)])
    store.add_leave("kim", [DAY])  # 중복 등록 무시
    assert store.snapshot(DAY).on_leave == {a}
    store.remove_leave("kim", [DAY])
    assert store.snapshot(DAY).on_leave == set()

    store.set_enabled("lee", False)
    assert [m.name for m in store.snapshot(DAY).members] == ["kim"]

    store.mark_blocked(a, DAY, "quota")
    store.unblock("kim", DAY)
    assert store.snapshot(DAY).daily[a].blocked_reason is None


def test_borrowings_report_only_other_people(store):
    kim = store.upsert_member("kim", "enc")
    store.upsert_member("lee", "enc")
    store.record_usage(kim, DAY, 10, 5, "kim", "m", 200)
    store.record_usage(kim, DAY, 100, 50, "lee", "m", 200)
    store.record_usage(kim, DAY, 100, 50, "lee", "m", 200)
    assert store.borrowings(DAY) == [("kim", "lee", 300, 2)]


def test_unknown_member_raises(store):
    with pytest.raises(ValueError):
        store.add_leave("nobody", [DAY])
