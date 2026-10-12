from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.config import Settings

ALGORITHM = "HS256"
ISSUER = "stage25-mini-api"
AUDIENCE = "stage25-users"
password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash("not-a-real-user-password")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: int, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
         "iss": ISSUER, "aud": AUDIENCE, "token_type": "access"},
        settings.jwt_secret_key.get_secret_value(), algorithm=ALGORITHM,
    )


def decode_user_id(token: str, settings: Settings) -> int:
    claims = jwt.decode(
        token, settings.jwt_secret_key.get_secret_value(), algorithms=[ALGORITHM], issuer=ISSUER, audience=AUDIENCE,
        options={"require": ["sub", "iat", "exp", "iss", "aud", "token_type"]},
    )
    subject = claims["sub"]
    if not isinstance(subject, str) or not subject.isascii() or not subject.isdecimal() or len(subject) > 19:
        raise InvalidTokenError("Invalid subject")
    user_id = int(subject)
    if not 1 <= user_id <= 2**63 - 1 or str(user_id) != subject or claims["token_type"] != "access":
        raise InvalidTokenError("Invalid subject or token type")
    if any(type(claims[field]) is not int for field in ("iat", "exp")) or claims["exp"] <= claims["iat"]:
        raise InvalidTokenError("Invalid timestamps")
    return user_id
