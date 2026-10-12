"""用户注册与重复记录处理。"""

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserCreate
from app.security import hash_password


class DuplicateUserError(Exception):
    pass


def user_exists(db: Session, username: str, email: str) -> bool:
    return db.scalar(select(User.id).where(or_(User.username == username, User.email == email))) is not None


def register_user(db: Session, body: UserCreate) -> User:
    if user_exists(db, body.username, str(body.email)):
        raise DuplicateUserError
    user = User(
        username=body.username,
        email=str(body.email),
        password_hash=hash_password(body.password.get_secret_value()),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # 预检查后仍可能出现并发注册；唯一约束是最终保障。
        db.rollback()
        if user_exists(db, body.username, str(body.email)):
            raise DuplicateUserError from None
        raise
    db.refresh(user)
    return user
