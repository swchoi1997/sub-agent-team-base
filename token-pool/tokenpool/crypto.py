"""API 키 암호화. DB에는 암호문만 저장하고, 복호화 키(TOKENPOOL_SECRET)는 팀원 PC 환경변수에만 둔다."""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken


def generate_secret() -> str:
    return Fernet.generate_key().decode()


class KeyCipher:
    def __init__(self, secret: str):
        try:
            self._fernet = Fernet(secret.encode())
        except (ValueError, TypeError) as exc:
            raise SystemExit("TOKENPOOL_SECRET 형식이 잘못됐습니다. `tokenpool gen-secret` 출력값을 쓰세요.") from exc
        self.decrypt = lru_cache(maxsize=256)(self._decrypt)

    def encrypt(self, api_key: str) -> str:
        return self._fernet.encrypt(api_key.encode()).decode()

    def _decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("키를 복호화할 수 없습니다 (TOKENPOOL_SECRET이 팀 값과 다름)") from exc
