from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from fastapi.security import OAuth2PasswordRequestFormStrict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_db
from app.dependencies import get_current_user, get_settings, require_admin, unauthorized
from app.models import User
from app.schemas import Page, Success, TaskCreate, TaskPatch, TaskRead, Token, UserCreate, UserRead
from app.security import DUMMY_HASH, create_access_token, verify_password
from app import services

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
TaskID = Annotated[int, Path(ge=1, le=2**63 - 1)]


@router.post("/auth/register", tags=["auth"], status_code=201, response_model=Success[UserRead], summary="注册普通用户")
def register(body: UserCreate, db: DB):
    return {"data": services.register_user(db, body)}


@router.post("/auth/token", tags=["auth"], response_model=Token, summary="表单登录并获取 access token")
def login(form: Annotated[OAuth2PasswordRequestFormStrict, Depends()], db: DB, settings: Annotated[Settings, Depends(get_settings)]):
    username = form.username.strip().lower()
    user = db.scalar(select(User).where(User.username == username)) if len(username) <= 30 else None
    # 过长密码不进入昂贵哈希运算；不存在用户仍进行一次固定哈希验证。
    password = form.password if len(form.password) <= 128 else "oversized-password-placeholder"
    valid = verify_password(password, user.password_hash if user else DUMMY_HASH)
    if user is None or not valid or len(form.password) > 128:
        raise unauthorized()
    if not user.is_active:
        raise HTTPException(403, "Inactive user")
    return Token(access_token=create_access_token(user.id, settings))


@router.get("/users/me", tags=["users"], response_model=Success[UserRead], summary="查看当前用户")
def me(user: CurrentUser):
    return {"data": user}


@router.get("/admin/users", tags=["admin"], response_model=Success[Page[UserRead]], summary="管理员查看用户列表")
def users(db: DB, admin: Annotated[User, Depends(require_admin)], page: Annotated[int, Query(ge=1, le=10000)] = 1, page_size: Annotated[int, Query(ge=1, le=100)] = 20):
    total = db.scalar(select(func.count()).select_from(User))
    items = list(db.scalars(select(User).order_by(User.id).offset((page - 1) * page_size).limit(page_size)))
    return {"data": {"items": items, "total": total, "page": page, "page_size": page_size}}


@router.post("/tasks", tags=["tasks"], status_code=201, response_model=Success[TaskRead], summary="创建自己的任务")
def create_task(body: TaskCreate, response: Response, user: CurrentUser, db: DB):
    task = services.create_task(db, user.id, body)
    response.headers["Location"] = f"/tasks/{task.id}"
    return {"data": task}


@router.get("/tasks", tags=["tasks"], response_model=Success[Page[TaskRead]], summary="分页查询自己的任务")
def tasks(
    user: CurrentUser, db: DB,
    page: Annotated[int, Query(ge=1, le=10000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    completed: bool | None = None,
    q: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    sort: Literal["id", "title", "priority"] = "id",
    order: Literal["asc", "desc"] = "asc",
):
    return {"data": services.list_tasks(db, user.id, page=page, page_size=page_size, completed=completed, q=q, sort=sort, order=order)}


@router.get("/tasks/{task_id}", tags=["tasks"], response_model=Success[TaskRead], summary="读取自己的任务")
def task(task_id: TaskID, user: CurrentUser, db: DB):
    return {"data": services.owned_task(db, task_id, user.id)}


@router.patch("/tasks/{task_id}", tags=["tasks"], response_model=Success[TaskRead], summary="部分更新自己的任务")
def patch_task(task_id: TaskID, body: TaskPatch, user: CurrentUser, db: DB):
    return {"data": services.update_task(db, services.owned_task(db, task_id, user.id), body)}


@router.delete("/tasks/{task_id}", tags=["tasks"], status_code=204, summary="删除自己的任务")
def delete_task(task_id: TaskID, user: CurrentUser, db: DB):
    db.delete(services.owned_task(db, task_id, user.id))
    db.commit()
    return Response(status_code=204)
