"""密码验证与 JWT 签发、验证。"""

from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.config import Settings

ALGORITHM = "HS256"
password_hasher = PasswordHash.recommended()
# 不存在的用户也执行一次密码校验，减少明显的耗时差异。
DUMMY_HASH = password_hasher.hash("dummy-password-not-used-for-login")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: int, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
            "token_type": "access",
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=ALGORITHM,
    )


def decode_user_id(token: str, settings: Settings) -> int:
    claims = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[ALGORITHM],
        options={"require": ["sub", "iat", "exp", "token_type"]},
    )
    subject = claims["sub"]
    if (
        claims["token_type"] != "access"
        or not isinstance(subject, str)
        or not subject.isascii()
        or not subject.isdecimal()
        or len(subject) > 19
    ):
        raise InvalidTokenError("Invalid access token subject or type")
    user_id = int(subject)
    if not 1 <= user_id <= 2**63 - 1:
        raise InvalidTokenError("Invalid user ID")
    return user_id
