"""认证依赖与账号可用性依赖分开，展示 401 和 403。"""

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.models import User
from app.security import decode_user_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if not token:
        raise unauthorized()
    try:
        user_id = decode_user_id(token, settings)
    except (InvalidTokenError, TypeError, ValueError):
        raise unauthorized() from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized()
    return user


def get_active_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return user
