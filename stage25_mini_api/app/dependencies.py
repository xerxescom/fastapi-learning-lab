from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_db
from app.models import User
from app.security import decode_user_id

oauth2 = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)


def get_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        raise HTTPException(503, "Application not ready")
    return settings


def unauthorized() -> HTTPException:
    return HTTPException(401, "Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    token: Annotated[str | None, Depends(oauth2)], db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if not token:
        raise unauthorized()
    try:
        user_id = decode_user_id(token, settings)
    except (InvalidTokenError, ValueError, TypeError):
        raise unauthorized() from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized()
    if not user.is_active:
        raise HTTPException(403, "Inactive user")
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    # 从数据库读取即时角色，不把 JWT 中的客户端声明当作授权依据。
    if user.role != "admin":
        raise HTTPException(403, "Not enough permissions")
    return user
