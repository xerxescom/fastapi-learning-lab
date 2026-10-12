"""公开的用户注册接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserRead
from app.services import DuplicateUserError, register_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: Annotated[Session, Depends(get_db)]) -> User:
    try:
        return register_user(db, body)
    except DuplicateUserError:
        raise HTTPException(status_code=409, detail="Username or email already registered") from None
