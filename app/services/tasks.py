from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


def create_task(
    db: Session,
    project: Project,
    payload: TaskCreate,
) -> Task:
    task = Task(
        project_id=project.id,
        **payload.model_dump(),
    )

    db.add(task)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(task)
    return task


def list_tasks(
    db: Session,
    project_id: int,
    limit: int,
    offset: int,
) -> tuple[list[Task], bool]:
    statement = (
        select(Task)
        .where(Task.project_id == project_id)
        .order_by(Task.created_at.desc(), Task.id.desc())
        .offset(offset)
        .limit(limit + 1)
    )

    tasks = list(db.scalars(statement).all())

    has_more = len(tasks) > limit

    return tasks[:limit], has_more


def get_task(
    db: Session,
    project_id: int,
    task_id: int,
) -> Task | None:
    statement = select(Task).where(
        Task.id == task_id,
        Task.project_id == project_id,
    )

    return db.scalar(statement)


def update_task(
    db: Session,
    task: Task,
    payload: TaskUpdate,
) -> Task:
    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(task, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(task)
    return task


def delete_task(
    db: Session,
    task: Task,
) -> None:
    try:
        db.delete(task)
        db.commit()
    except Exception:
        db.rollback()
        raise
