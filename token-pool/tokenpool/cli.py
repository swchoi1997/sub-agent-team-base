"""tokenpool 명령줄 도구."""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import logging
import sys
import unicodedata
from zoneinfo import ZoneInfo

from . import config as config_mod
from .config import Config
from .crypto import KeyCipher, generate_secret
from .db import Store, utcnow


def _today(cfg: Config) -> dt.date:
    return dt.datetime.now(ZoneInfo(cfg.timezone)).date()


def _parse_day(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"날짜 형식은 YYYY-MM-DD 입니다: {value}") from exc


def _day_range(start: dt.date, end: dt.date | None) -> list[dt.date]:
    end = end or start
    if end < start:
        raise SystemExit("--to 날짜가 시작 날짜보다 빠릅니다.")
    return [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]


def _width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def _ljust(text: str, width: int) -> str:
    return text + " " * max(0, width - _width(text))


def _rjust(text: str, width: int) -> str:
    return " " * max(0, width - _width(text)) + text


def _fmt_tokens(n: int | None) -> str:
    if n is None:
        return "-"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


# ---- commands -----------------------------------------------------------
def cmd_gen_secret(args) -> None:
    print(generate_secret())
    print(
        "\n↑ 팀 공통 시크릿입니다. 팀원끼리만 안전하게 공유하고, 각자 환경변수 TOKENPOOL_SECRET에 설정하세요.",
        file=sys.stderr,
    )


def cmd_init(args) -> None:
    cipher = KeyCipher(config_mod.get_secret())
    path = config_mod.config_path()
    previous = config_mod.load(path) if path.exists() else None
    cfg = Config(
        me=args.name or (previous.me if previous else None) or input("내 이름(팀 내 고유): ").strip(),
        db_url=args.db_url or (previous.db_url if previous else None) or input("공유 DB URL: ").strip(),
        upstream=args.upstream or (previous.upstream if previous else None) or input("사내 LLM 주소: ").strip(),
    )
    if previous:
        for field in ("auth_header", "host", "port", "timezone", "borrow_ratio", "max_attempts", "short_cooldown_max"):
            setattr(cfg, field, getattr(previous, field))
    if args.auth_header:
        cfg.auth_header = args.auth_header
    if args.port:
        cfg.port = args.port

    api_key = sys.stdin.readline().strip() if args.api_key_stdin else getpass.getpass("내 사내 LLM API 키: ").strip()
    if not api_key:
        raise SystemExit("API 키가 비어 있습니다.")

    store = Store(cfg.db_url)
    store.create_all()
    store.upsert_member(cfg.me, cipher.encrypt(api_key))
    saved = config_mod.save(cfg, path)
    print(f"등록 완료: {cfg.me} → 풀에 키가 들어갔습니다.")
    print(f"설정 파일: {saved}")
    print(
        "\nClaude Code 설정(~/.claude/settings.json):\n"
        '  "env": {\n'
        f'    "ANTHROPIC_BASE_URL": "http://{cfg.host}:{cfg.port}",\n'
        '    "ANTHROPIC_AUTH_TOKEN": "tokenpool-local"\n'
        "  }\n"
        "그 다음 `tokenpool serve`를 켜 두세요."
    )


def cmd_serve(args) -> None:
    import uvicorn

    from .proxy import TokenPoolProxy, create_app

    cfg = config_mod.load()
    cfg.port = args.port or cfg.port
    store = Store(cfg.db_url)
    store.create_all()
    if store.member_id(cfg.me) is None:
        raise SystemExit(f"{cfg.me}은(는) 풀에 등록돼 있지 않습니다. `tokenpool init`을 먼저 실행하세요.")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    proxy = TokenPoolProxy(cfg, store, KeyCipher(config_mod.get_secret()))
    print(f"tokenpool 프록시: http://{cfg.host}:{cfg.port} → {cfg.upstream}  (나: {cfg.me})")
    uvicorn.run(create_app(proxy), host=cfg.host, port=cfg.port, log_level="warning")


def cmd_leave(args) -> None:
    cfg = config_mod.load()
    store = Store(cfg.db_url)
    days = _day_range(args.date or _today(cfg), args.to)
    name = args.name or cfg.me
    if args.cancel:
        store.remove_leave(name, days)
        print(f"{name} 연차 취소: {days[0]} ~ {days[-1]}")
    else:
        store.add_leave(name, days)
        print(f"{name} 연차 등록: {days[0]} ~ {days[-1]} — 이 기간 키를 팀이 우선해서 씁니다.")


def cmd_status(args) -> None:
    cfg = config_mod.load()
    store = Store(cfg.db_url)
    day = args.date or _today(cfg)
    now = utcnow()
    print(f"[{day}] 팀 토큰 풀 현황 (기준 시간대 {cfg.timezone})\n")
    print(_ljust(" 이름", 13) + _ljust("상태", 16) + _rjust("오늘 사용", 10) + _rjust("요청", 7) + _rjust("추정 한도", 11))
    print("-" * 57)
    for r in store.status(day):
        if not r.enabled:
            state = "비활성"
        elif r.blocked_reason == "quota":
            state = "오늘 소진"
        elif r.blocked_reason == "auth":
            state = "키 오류"
        elif r.cooldown_until and r.cooldown_until > now:
            state = "잠시 쉬는 중"
        elif r.on_leave:
            state = "연차(공유 우선)"
        else:
            state = "사용 가능"
        mark = "*" if r.name == cfg.me else " "
        print(
            mark
            + _ljust(r.name, 12)
            + _ljust(state, 16)
            + _rjust(_fmt_tokens(r.used_in + r.used_out), 10)
            + _rjust(str(r.requests), 7)
            + _rjust(_fmt_tokens(r.learned_limit), 11)
        )
    borrowings = store.borrowings(day)
    if borrowings:
        print("\n빌려 쓴 내역 (키 소유자 ← 실제 사용자)")
        for owner, user, tokens, count in borrowings:
            print(f"  {owner} ← {user}: {_fmt_tokens(tokens)} 토큰 / {count}회")


def cmd_enable(args, enabled: bool) -> None:
    cfg = config_mod.load()
    store = Store(cfg.db_url)
    name = args.name or cfg.me
    store.set_enabled(name, enabled)
    print(f"{name} 키를 풀에 {'다시 넣었습니다' if enabled else '서 뺐습니다 (opt-out)'}.")


def cmd_unblock(args) -> None:
    cfg = config_mod.load()
    store = Store(cfg.db_url)
    store.unblock(args.name, args.date or _today(cfg))
    print(f"{args.name} 키를 다시 사용 가능으로 돌렸습니다.")


# ---- entry --------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tokenpool", description="팀 사내 LLM 토큰 공유 프록시")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("gen-secret", help="팀 공통 암호화 시크릿 생성 (팀에서 1회)").set_defaults(func=cmd_gen_secret)

    s = sub.add_parser("init", help="내 키를 풀에 등록하고 로컬 설정 생성")
    s.add_argument("--name")
    s.add_argument("--db-url")
    s.add_argument("--upstream", help="사내 LLM 주소 (Anthropic 호환)")
    s.add_argument("--auth-header", help="키 헤더 이름 (기본 x-api-key, Bearer면 authorization)")
    s.add_argument("--port", type=int)
    s.add_argument("--api-key-stdin", action="store_true", help="키를 표준입력 한 줄로 받기")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("serve", help="로컬 프록시 실행")
    s.add_argument("--port", type=int)
    s.set_defaults(func=cmd_serve)

    s = sub.add_parser("leave", help="연차 등록/취소 (기본: 오늘)")
    s.add_argument("date", nargs="?", type=_parse_day)
    s.add_argument("--to", type=_parse_day, help="마지막 날짜 (기간 등록)")
    s.add_argument("--cancel", action="store_true")
    s.add_argument("--name", help="다른 팀원 대신 등록")
    s.set_defaults(func=cmd_leave)

    s = sub.add_parser("status", help="오늘 키별 사용량과 빌려 쓴 내역")
    s.add_argument("--date", type=_parse_day)
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("disable", help="내 키를 풀에서 빼기")
    s.add_argument("--name")
    s.set_defaults(func=lambda a: cmd_enable(a, False))

    s = sub.add_parser("enable", help="내 키를 풀에 다시 넣기")
    s.add_argument("--name")
    s.set_defaults(func=lambda a: cmd_enable(a, True))

    s = sub.add_parser("unblock", help="잘못 소진 처리된 키를 오늘 다시 사용 가능으로")
    s.add_argument("name")
    s.add_argument("--date", type=_parse_day)
    s.set_defaults(func=cmd_unblock)
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
