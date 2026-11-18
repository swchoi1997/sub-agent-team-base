import datetime as dt

from tokenpool.selector import DailyState, KeyInfo, Snapshot, rank

NOW = dt.datetime(2026, 11, 18, 3, 0)


def keys(*names, **overrides):
    out = []
    for i, name in enumerate(names, start=1):
        out.append(KeyInfo(id=i, name=name, api_key_enc=f"enc-{name}", **overrides.get(name, {})))
    return out


def names(ranked):
    return [k.name for k in ranked]


def test_own_key_first_then_leave_then_others_by_usage():
    members = keys("me", "busy", "idle", "vacation")
    snap = Snapshot(
        members=members,
        daily={2: DailyState(used_in=900), 3: DailyState(used_in=10), 4: DailyState(used_in=500)},
        on_leave={4},
    )
    assert names(rank(snap, me_id=1, now=NOW, borrow_ratio=0.5)) == ["me", "vacation", "idle", "busy"]


def test_blocked_and_cooldown_keys_are_skipped():
    members = keys("me", "a", "b", b={"cooldown_until": NOW + dt.timedelta(seconds=30)})
    snap = Snapshot(members=members, daily={1: DailyState(blocked_reason="quota")})
    assert names(rank(snap, me_id=1, now=NOW, borrow_ratio=0.5)) == ["a"]


def test_expired_cooldown_is_available_again():
    members = keys("me", a={"cooldown_until": NOW - dt.timedelta(seconds=1)})
    assert names(rank(Snapshot(members=members), me_id=None, now=NOW, borrow_ratio=0.5)) == ["me"]


def test_owner_share_is_protected_when_not_on_leave():
    members = keys("me", "worker", "vacation", worker={"learned_limit": 1000}, vacation={"learned_limit": 1000})
    snap = Snapshot(
        members=members,
        daily={
            1: DailyState(blocked_reason="quota"),
            2: DailyState(used_in=500),  # 50% 도달 → 빌려 쓰지 않음
            3: DailyState(used_in=900),  # 연차라 끝까지 사용
        },
        on_leave={3},
    )
    assert names(rank(snap, me_id=1, now=NOW, borrow_ratio=0.5)) == ["vacation"]


def test_owner_can_always_use_own_key_beyond_ratio():
    members = keys("me", me={"learned_limit": 1000})
    snap = Snapshot(members=members, daily={1: DailyState(used_in=990)})
    assert names(rank(snap, me_id=1, now=NOW, borrow_ratio=0.5)) == ["me"]


def test_sticky_borrowed_key_kept_while_own_key_blocked():
    members = keys("me", "a", "b")
    snap = Snapshot(
        members=members,
        daily={1: DailyState(blocked_reason="quota"), 2: DailyState(used_in=10), 3: DailyState(used_in=200)},
    )
    assert names(rank(snap, me_id=1, now=NOW, borrow_ratio=0.5, sticky_id=3)) == ["b", "a"]


def test_sticky_ignored_when_own_key_available():
    members = keys("me", "a")
    snap = Snapshot(members=members)
    assert names(rank(snap, me_id=1, now=NOW, borrow_ratio=0.5, sticky_id=2)) == ["me", "a"]


def test_unregistered_user_only_borrows():
    members = keys("a", "b")
    snap = Snapshot(members=members, daily={1: DailyState(used_in=50)})
    assert names(rank(snap, me_id=None, now=NOW, borrow_ratio=0.5)) == ["b", "a"]
