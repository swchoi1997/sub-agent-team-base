"""로컬 설정(~/.tokenpool/config.toml)과 팀 공통 시크릿."""

from __future__ import annotations

import json
import os
import tomllib
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass
class Config:
    me: str  # 내 이름 (members.name)
    db_url: str  # 공유 DB (예: postgresql+psycopg://user:pw@db-host/tokenpool)
    upstream: str  # 사내 LLM 주소 (Anthropic 호환, 예: https://llm.internal)
    auth_header: str = "x-api-key"  # 사내 LLM이 키를 받는 헤더. "authorization"이면 Bearer로 보냄
    host: str = "127.0.0.1"
    port: int = 8787
    timezone: str = "Asia/Seoul"  # 일일 한도가 초기화되는 기준 시간대
    borrow_ratio: float = 0.5  # 출근한 소유자 키는 학습된 한도의 이 비율까지만 남이 사용
    max_attempts: int = 6  # 요청 하나당 시도할 최대 키 개수
    short_cooldown_max: int = 600  # 429의 retry-after가 이 초 이하면 일시 제한으로 보고 쿨다운만


def config_path() -> Path:
    env = os.environ.get("TOKENPOOL_CONFIG")
    return Path(env) if env else Path.home() / ".tokenpool" / "config.toml"


def load(path: Path | None = None) -> Config:
    path = path or config_path()
    if not path.exists():
        raise SystemExit(f"설정 파일이 없습니다: {path}\n먼저 `tokenpool init`을 실행하세요.")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    known = {f.name for f in fields(Config)}
    return Config(**{k: v for k, v in data.items() if k in known})


def save(cfg: Config, path: Path | None = None) -> Path:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, value in asdict(cfg).items():
        # JSON 문자열 이스케이프는 TOML basic string과 호환됨
        lines.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def get_secret() -> str:
    secret = os.environ.get("TOKENPOOL_SECRET")
    if not secret:
        raise SystemExit(
            "환경변수 TOKENPOOL_SECRET이 없습니다.\n"
            "팀에서 한 명이 `tokenpool gen-secret`으로 만든 값을 팀원끼리 안전하게 공유해 설정하세요."
        )
    return secret
