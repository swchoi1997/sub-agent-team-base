"""어떤 키로 요청을 보낼지 정하는 순수 로직 (DB·네트워크 없음)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


@dataclass(frozen=True)
class KeyInfo:
    id: int
    name: str
    api_key_enc: str
    learned_limit: int | None = None  # 429가 났을 때의 하루 누적 사용량 = 추정 일일 한도
    cooldown_until: dt.datetime | None = None  # 짧은 rate limit으로 잠깐 쉬는 중 (UTC naive)


@dataclass
class DailyState:
    used_in: int = 0
    used_out: int = 0
    requests: int = 0
    blocked_reason: str | None = None  # 'quota'(오늘 한도 소진) | 'auth'(키 무효)

    @property
    def used(self) -> int:
        return self.used_in + self.used_out


@dataclass
class Snapshot:
    members: list[KeyInfo]
    daily: dict[int, DailyState] = field(default_factory=dict)
    on_leave: set[int] = field(default_factory=set)

    def used(self, member_id: int) -> int:
        state = self.daily.get(member_id)
        return state.used if state else 0


def rank(
    snap: Snapshot,
    me_id: int | None,
    now: dt.datetime,
    borrow_ratio: float,
    sticky_id: int | None = None,
) -> list[KeyInfo]:
    """시도할 키 순서: 내 키 → 오늘 연차인 사람 키 → 나머지 팀원 키 (그룹 안에서는 오늘 덜 쓴 순).

    - 오늘 막힌 키, 쿨다운 중인 키는 제외한다.
    - 출근한 팀원 키는 학습된 한도의 borrow_ratio를 넘으면 남이 쓰지 않는다 (본인 몫 보호).
    - 내 키가 막혀 남의 키를 빌려 쓰는 중이면, 직전에 성공한 키(sticky)를 계속 쓴다 (프롬프트 캐시 유지).
    """
    available: list[KeyInfo] = []
    for m in snap.members:
        state = snap.daily.get(m.id)
        if state and state.blocked_reason:
            continue
        if m.cooldown_until and m.cooldown_until > now:
            continue
        available.append(m)

    mine = [m for m in available if m.id == me_id]
    leave = sorted(
        (m for m in available if m.id != me_id and m.id in snap.on_leave),
        key=lambda m: (snap.used(m.id), m.id),
    )
    others = sorted(
        (
            m
            for m in available
            if m.id != me_id
            and m.id not in snap.on_leave
            and not (m.learned_limit and snap.used(m.id) >= borrow_ratio * m.learned_limit)
        ),
        key=lambda m: (snap.used(m.id), m.id),
    )

    borrowed = leave + others
    if not mine and sticky_id is not None:
        for i, m in enumerate(borrowed):
            if m.id == sticky_id:
                borrowed.insert(0, borrowed.pop(i))
                break
    return mine + borrowed
