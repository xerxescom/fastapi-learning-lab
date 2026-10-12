from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import BusinessError
from app.models import Task, User
from app.schemas import Page, TaskCreate, TaskPatch, TaskRead, UserCreate
from app.security import hash_password


def register_user(db: Session, body: UserCreate) -> User:
    user = User(username=body.username, email=str(body.email), password_hash=hash_password(body.password.get_secret_value()))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessError(409, "USER_EXISTS", "Username or email already exists") from None
    db.refresh(user)
    return user


def owned_task(db: Session, task_id: int, owner_id: int) -> Task:
    task = db.scalar(select(Task).where(Task.id == task_id, Task.owner_id == owner_id))
    if task is None:
        # 不区分不存在与不属于自己，避免泄露他人的任务是否存在。
        raise BusinessError(404, "TASK_NOT_FOUND", "Task not found")
    return task


def save_task(db: Session, task: Task) -> Task:
    db.add(task)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessError(409, "TASK_CONFLICT", "Task could not be saved") from None
    db.refresh(task)
    return task


def create_task(db: Session, owner_id: int, body: TaskCreate) -> Task:
    return save_task(db, Task(owner_id=owner_id, **body.model_dump()))


def update_task(db: Session, task: Task, body: TaskPatch) -> Task:
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    return save_task(db, task)


def list_tasks(db: Session, owner_id: int, *, page: int, page_size: int, completed: bool | None, q: str | None, sort: str, order: str):
    conditions = [Task.owner_id == owner_id]
    if completed is not None:
        conditions.append(Task.completed == completed)
    if q is not None:
        conditions.append(Task.title.contains(q, autoescape=True))
    total = db.scalar(select(func.count()).select_from(Task).where(*conditions))
    column = {"id": Task.id, "title": Task.title, "priority": Task.priority}[sort]
    ordering = column.desc() if order == "desc" else column.asc()
    # 非唯一排序字段追加 ID，避免相同优先级/标题的记录跨页漂移。
    statement = select(Task).where(*conditions).order_by(ordering, Task.id.asc()).offset((page - 1) * page_size).limit(page_size)
    items = [TaskRead.model_validate(task) for task in db.scalars(statement)]
    return Page[TaskRead](items=items, total=total, page=page, page_size=page_size)
