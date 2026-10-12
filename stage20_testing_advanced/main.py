"""Stage 20：任务清单 API，提供可替换的数据库和业务策略依赖。"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import build_engine, get_db
from app.models import Task
from app.schemas import TaskCreate, TaskRead, TaskUpdate
from app.services import CapacityExceeded, DuplicateTask, TaskPolicy, create_task, get_policy


def create_app(database_url: str | None = None) -> FastAPI:
    database_url = database_url or f"sqlite:///{(Path(__file__).parent / 'tasks.db').as_posix()}"
    engine = build_engine(database_url)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="Stage 20：测试进阶", lifespan=lifespan)
    application.state.engine = engine

    @application.post("/tasks", status_code=201, response_model=TaskRead)
    def add_task(body: TaskCreate, db: Annotated[Session, Depends(get_db)], policy: Annotated[TaskPolicy, Depends(get_policy)]) -> Task:
        try:
            return create_task(db, body.title, policy)
        except CapacityExceeded:
            raise HTTPException(409, "Task capacity reached") from None
        except DuplicateTask:
            raise HTTPException(409, "Task title already exists") from None

    @application.get("/tasks", response_model=list[TaskRead])
    def list_tasks(
        db: Annotated[Session, Depends(get_db)],
        completed: bool | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 10,
        offset: Annotated[int, Query(ge=0, le=10000)] = 0,
    ) -> list[Task]:
        query = select(Task)
        if completed is not None:
            query = query.where(Task.completed == completed)
        return list(db.scalars(query.order_by(Task.id).limit(limit).offset(offset)).all())

    def find_task(task_id: int, db: Session) -> Task:
        task = db.get(Task, task_id)
        if task is None:
            raise HTTPException(404, "Task not found")
        return task

    @application.get("/tasks/{task_id}", response_model=TaskRead)
    def read_task(task_id: int, db: Annotated[Session, Depends(get_db)]) -> Task:
        return find_task(task_id, db)

    @application.patch("/tasks/{task_id}", response_model=TaskRead)
    def update_task(task_id: int, body: TaskUpdate, db: Annotated[Session, Depends(get_db)]) -> Task:
        task = find_task(task_id, db)
        task.completed = body.completed
        db.commit()
        db.refresh(task)
        return task

    @application.delete("/tasks/{task_id}", status_code=204)
    def delete_task(task_id: int, db: Annotated[Session, Depends(get_db)]) -> Response:
        db.delete(find_task(task_id, db))
        db.commit()
        return Response(status_code=204)

    return application


app = create_app()
