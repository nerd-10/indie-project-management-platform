from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from app.services.projects import get_project
from app.services.tasks import (
    create_task,
    delete_task,
    get_task,
    list_tasks,
    update_task,
)

router = APIRouter(
    prefix="/projects/{project_id}/tasks",
    tags=["Tasks"],
)


def get_owned_project(
    db: Session,
    project_id: int,
    user_id: int,
) -> Project:
    project = get_project(
        db=db,
        project_id=project_id,
        user_id=user_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


def get_project_task(
    db: Session,
    project_id: int,
    task_id: int,
    user_id: int,
) -> Task:
    get_owned_project(db, project_id, user_id)

    task = get_task(
        db=db,
        project_id=project_id,
        task_id=task_id,
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_task(
    project_id: int,
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    project = get_owned_project(
        db,
        project_id,
        current_user.id,
    )

    return create_task(
        db=db,
        project=project,
        payload=payload,
    )


@router.get(
    "",
    response_model=TaskListResponse,
    status_code=status.HTTP_200_OK,
)
def get_tasks(
    project_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskListResponse:
    get_owned_project(
        db,
        project_id,
        current_user.id,
    )

    tasks, has_more = list_tasks(
        db=db,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )

    return TaskListResponse(
        items=tasks,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
)
def retrieve_task(
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    return get_project_task(
        db,
        project_id,
        task_id,
        current_user.id,
    )


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
)
def patch_task(
    project_id: int,
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    task = get_project_task(
        db,
        project_id,
        task_id,
        current_user.id,
    )

    return update_task(
        db=db,
        task=task,
        payload=payload,
    )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_task(
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    task = get_project_task(
        db,
        project_id,
        task_id,
        current_user.id,
    )

    delete_task(
        db=db,
        task=task,
    )
