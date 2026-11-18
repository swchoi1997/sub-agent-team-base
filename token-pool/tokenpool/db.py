"""공유 DB 접근. 운영은 Postgres/MySQL, 테스트는 SQLite. 모든 시각은 UTC naive로 저장한다."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError

from .selector import DailyState, KeyInfo, Snapshot

metadata = MetaData()

members = Table(
    "tp_members",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(100), nullable=False, unique=True),
    Column("api_key_enc", Text, nullable=False),
    Column("enabled", Boolean, nullable=False, default=True),
    Column("learned_limit", BigInteger, nullable=True),
    Column("cooldown_until", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=False),
)

key_daily = Table(
    "tp_key_daily",
    metadata,
    Column("member_id", Integer, ForeignKey("tp_members.id"), primary_key=True),
    Column("day", Date, primary_key=True),
    Column("used_in", BigInteger, nullable=False, default=0),
    Column("used_out", BigInteger, nullable=False, default=0),
    Column("requests", Integer, nullable=False, default=0),
    Column("blocked_reason", String(20), nullable=True),
    Column("blocked_at", DateTime, nullable=True),
)

leave = Table(
    "tp_leave",
    metadata,
    Column("member_id", Integer, ForeignKey("tp_members.id"), primary_key=True),
    Column("day", Date, primary_key=True),
)

usage_log = Table(
    "tp_usage_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ts", DateTime, nullable=False),
    Column("day", Date, nullable=False, index=True),
    Column("key_owner_id", Integer, ForeignKey("tp_members.id"), nullable=False),
    Column("actual_user", String(100), nullable=False),
    Column("model", String(200), nullable=True),
    Column("in_tokens", BigInteger, nullable=False, default=0),
    Column("out_tokens", BigInteger, nullable=False, default=0),
    Column("status", Integer, nullable=False),
)


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


@dataclass
class StatusRow:
    name: str
    enabled: bool
    on_leave: bool
    used_in: int
    used_out: int
    requests: int
    blocked_reason: str | None
    cooldown_until: dt.datetime | None
    learned_limit: int | None


class Store:
    def __init__(self, url: str):
        kwargs = {"future": True, "pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
        self.engine = create_engine(url, **kwargs)

    def create_all(self) -> None:
        metadata.create_all(self.engine)

    # ---- members ---------------------------------------------------------
    def upsert_member(self, name: str, api_key_enc: str) -> int:
        with self.engine.begin() as conn:
            row = conn.execute(select(members.c.id).where(members.c.name == name)).first()
            if row:
                conn.execute(
                    update(members)
                    .where(members.c.id == row.id)
                    .values(api_key_enc=api_key_enc, enabled=True, learned_limit=None, cooldown_until=None)
                )
                return row.id
            result = conn.execute(
                insert(members).values(name=name, api_key_enc=api_key_enc, enabled=True, created_at=utcnow())
            )
            return result.inserted_primary_key[0]

    def member_id(self, name: str) -> int | None:
        with self.engine.connect() as conn:
            row = conn.execute(select(members.c.id).where(members.c.name == name)).first()
            return row.id if row else None

    def _require_member(self, name: str) -> int:
        member_id = self.member_id(name)
        if member_id is None:
            raise ValueError(f"등록되지 않은 팀원입니다: {name}")
        return member_id

    def set_enabled(self, name: str, enabled: bool) -> None:
        member_id = self._require_member(name)
        with self.engine.begin() as conn:
            conn.execute(update(members).where(members.c.id == member_id).values(enabled=enabled))

    def unblock(self, name: str, day: dt.date) -> None:
        """잘못 막힌 키(예: 일시 rate limit을 일일 소진으로 오인)를 오늘 다시 풀에 넣는다."""
        member_id = self._require_member(name)
        with self.engine.begin() as conn:
            conn.execute(
                update(key_daily)
                .where(key_daily.c.member_id == member_id, key_daily.c.day == day)
                .values(blocked_reason=None, blocked_at=None)
            )
            conn.execute(update(members).where(members.c.id == member_id).values(cooldown_until=None))

    # ---- leave -----------------------------------------------------------
    def add_leave(self, name: str, days: list[dt.date]) -> None:
        member_id = self._require_member(name)
        with self.engine.begin() as conn:
            existing = {
                r.day
                for r in conn.execute(
                    select(leave.c.day).where(leave.c.member_id == member_id, leave.c.day.in_(days))
                )
            }
            new = [{"member_id": member_id, "day": d} for d in days if d not in existing]
            if new:
                conn.execute(insert(leave), new)

    def remove_leave(self, name: str, days: list[dt.date]) -> None:
        member_id = self._require_member(name)
        with self.engine.begin() as conn:
            conn.execute(delete(leave).where(leave.c.member_id == member_id, leave.c.day.in_(days)))

    # ---- proxy hot path --------------------------------------------------
    def snapshot(self, day: dt.date) -> Snapshot:
        with self.engine.connect() as conn:
            member_rows = conn.execute(select(members).where(members.c.enabled.is_(True))).all()
            daily_rows = conn.execute(select(key_daily).where(key_daily.c.day == day)).all()
            leave_rows = conn.execute(select(leave.c.member_id).where(leave.c.day == day)).all()
        return Snapshot(
            members=[
                KeyInfo(
                    id=r.id,
                    name=r.name,
                    api_key_enc=r.api_key_enc,
                    learned_limit=r.learned_limit,
                    cooldown_until=r.cooldown_until,
                )
                for r in member_rows
            ],
            daily={
                r.member_id: DailyState(
                    used_in=r.used_in, used_out=r.used_out, requests=r.requests, blocked_reason=r.blocked_reason
                )
                for r in daily_rows
            },
            on_leave={r.member_id for r in leave_rows},
        )

    def _ensure_daily(self, conn, member_id: int, day: dt.date) -> None:
        values = {"member_id": member_id, "day": day, "used_in": 0, "used_out": 0, "requests": 0}
        dialect = conn.dialect.name
        if dialect in ("sqlite", "postgresql"):
            if dialect == "sqlite":
                from sqlalchemy.dialects.sqlite import insert as dialect_insert
            else:
                from sqlalchemy.dialects.postgresql import insert as dialect_insert
            conn.execute(dialect_insert(key_daily).values(**values).on_conflict_do_nothing())
        elif dialect in ("mysql", "mariadb"):
            conn.execute(insert(key_daily).values(**values).prefix_with("IGNORE"))
        else:
            try:
                with conn.begin_nested():
                    conn.execute(insert(key_daily).values(**values))
            except IntegrityError:
                pass

    def record_usage(
        self,
        member_id: int,
        day: dt.date,
        in_tokens: int,
        out_tokens: int,
        actual_user: str,
        model: str | None,
        status: int,
    ) -> None:
        with self.engine.begin() as conn:
            self._ensure_daily(conn, member_id, day)
            conn.execute(
                update(key_daily)
                .where(key_daily.c.member_id == member_id, key_daily.c.day == day)
                .values(
                    used_in=key_daily.c.used_in + in_tokens,
                    used_out=key_daily.c.used_out + out_tokens,
                    requests=key_daily.c.requests + 1,
                )
            )
            conn.execute(
                insert(usage_log).values(
                    ts=utcnow(),
                    day=day,
                    key_owner_id=member_id,
                    actual_user=actual_user,
                    model=model,
                    in_tokens=in_tokens,
                    out_tokens=out_tokens,
                    status=status,
                )
            )

    def mark_blocked(self, member_id: int, day: dt.date, reason: str) -> None:
        with self.engine.begin() as conn:
            self._ensure_daily(conn, member_id, day)
            row = conn.execute(
                select(key_daily.c.used_in, key_daily.c.used_out, key_daily.c.blocked_reason).where(
                    key_daily.c.member_id == member_id, key_daily.c.day == day
                )
            ).one()
            if row.blocked_reason:
                return  # 다른 팀원 프록시가 먼저 기록함
            conn.execute(
                update(key_daily)
                .where(key_daily.c.member_id == member_id, key_daily.c.day == day)
                .values(blocked_reason=reason, blocked_at=utcnow())
            )
            used = row.used_in + row.used_out
            if reason == "quota" and used > 0:
                conn.execute(update(members).where(members.c.id == member_id).values(learned_limit=used))

    def set_cooldown(self, member_id: int, until: dt.datetime) -> None:
        with self.engine.begin() as conn:
            conn.execute(update(members).where(members.c.id == member_id).values(cooldown_until=until))

    # ---- reporting -------------------------------------------------------
    def status(self, day: dt.date) -> list[StatusRow]:
        with self.engine.connect() as conn:
            member_rows = conn.execute(select(members).order_by(members.c.name)).all()
            daily = {r.member_id: r for r in conn.execute(select(key_daily).where(key_daily.c.day == day))}
            on_leave = {r.member_id for r in conn.execute(select(leave.c.member_id).where(leave.c.day == day))}
        rows = []
        for m in member_rows:
            d = daily.get(m.id)
            rows.append(
                StatusRow(
                    name=m.name,
                    enabled=m.enabled,
                    on_leave=m.id in on_leave,
                    used_in=d.used_in if d else 0,
                    used_out=d.used_out if d else 0,
                    requests=d.requests if d else 0,
                    blocked_reason=d.blocked_reason if d else None,
                    cooldown_until=m.cooldown_until,
                    learned_limit=m.learned_limit,
                )
            )
        return rows

    def borrowings(self, day: dt.date) -> list[tuple[str, str, int, int]]:
        """(키 소유자, 실제 사용자, 토큰 합계, 요청 수) — 남의 키를 쓴 내역만."""
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(
                    members.c.name,
                    usage_log.c.actual_user,
                    func.sum(usage_log.c.in_tokens + usage_log.c.out_tokens),
                    func.count(),
                )
                .join(members, members.c.id == usage_log.c.key_owner_id)
                .where(usage_log.c.day == day, usage_log.c.actual_user != members.c.name)
                .group_by(members.c.name, usage_log.c.actual_user)
                .order_by(members.c.name, usage_log.c.actual_user)
            ).all()
        return [(r[0], r[1], int(r[2] or 0), int(r[3])) for r in rows]
