"""注册、表单登录及受保护接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import get_active_user, unauthorized
from app.models import User
from app.schemas import Token, UserCreate, UserRead
from app.security import DUMMY_HASH, create_access_token, verify_password
from app.services import DuplicateUserError, register_user

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
ActiveUser = Annotated[User, Depends(get_active_user)]


@router.post("/users", response_model=UserRead, status_code=201, tags=["users"])
def create_user(body: UserCreate, db: DbSession) -> User:
    try:
        return register_user(db, body)
    except DuplicateUserError:
        raise HTTPException(status_code=409, detail="Username or email already registered") from None


@router.post("/token", response_model=Token, tags=["auth"])
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Token:
    username = form.username.strip().lower()
    user = db.scalar(select(User).where(User.username == username))
    password_hash = user.password_hash if user is not None else DUMMY_HASH
    valid = verify_password(form.password, password_hash)
    if user is None or not valid:
        raise unauthorized()
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return Token(access_token=create_access_token(user.id, settings))


@router.get("/users/me", response_model=UserRead, tags=["users"])
def read_current_user(user: ActiveUser) -> User:
    return user


@router.get("/items", tags=["items"])
def read_protected_items(user: ActiveUser) -> dict:
    return {"owner": user.username, "items": [{"name": "Learning notebook"}]}
