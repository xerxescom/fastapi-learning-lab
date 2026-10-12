"""认证、账号状态与权限校验依赖。"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.models import User
from app.permissions import ROLE_PERMISSIONS, Permission
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


def require_permission(permission: Permission) -> Callable[..., User]:
    def check_permission(user: Annotated[User, Depends(get_active_user)]) -> User:
        # 每次请求读取当前数据库角色，不信任 token 或客户端提供的角色。
        if permission not in ROLE_PERMISSIONS.get(user.role, frozenset()):
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return user

    return check_permission
