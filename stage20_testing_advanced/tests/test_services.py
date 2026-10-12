import pytest
from sqlalchemy import func, select

from app.models import Task
from app.services import CapacityExceeded, DuplicateTask, TaskPolicy, create_task

pytestmark = pytest.mark.integration


def test_duplicate_rollback_leaves_same_session_usable(db_session):
    policy = TaskPolicy(max_tasks=10)
    create_task(db_session, "same", policy)
    with pytest.raises(DuplicateTask):
        create_task(db_session, "same", policy)
    # 不经过 HTTP，直接验证发生唯一冲突后的同一个 Session 可以继续使用。
    created = create_task(db_session, "next", policy)
    assert created.title == "next"
    assert db_session.scalar(select(func.count()).select_from(Task)) == 2


def test_capacity_error_does_not_insert(db_session):
    with pytest.raises(CapacityExceeded):
        create_task(db_session, "blocked", TaskPolicy(max_tasks=0))
    assert db_session.scalar(select(func.count()).select_from(Task)) == 0
