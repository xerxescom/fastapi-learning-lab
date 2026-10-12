from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Task


@dataclass(frozen=True)
class TaskPolicy:
    max_tasks: int = 100


def get_policy() -> TaskPolicy:
    return TaskPolicy()


class CapacityExceeded(Exception):
    pass


class DuplicateTask(Exception):
    pass


def ensure_capacity(current: int, maximum: int) -> None:
    if current >= maximum:
        raise CapacityExceeded


def create_task(db: Session, title: str, policy: TaskPolicy) -> Task:
    current = db.scalar(select(func.count()).select_from(Task))
    ensure_capacity(current, policy.max_tasks)
    task = Task(title=title)
    db.add(task)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateTask from None
    db.refresh(task)
    return task
