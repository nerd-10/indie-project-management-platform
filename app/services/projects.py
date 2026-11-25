from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


def create_project(db: Session, payload: ProjectCreate, user_id: int) -> Project:
    project = Project(
        owner_id=user_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(project)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(project)

    return project


def list_projects(
    db: Session,
    user_id: int,
    limit: int,
    offset: int,
) -> tuple[list[Project], bool]:
    statement = (
        select(Project)
        .where(Project.owner_id == user_id)
        .order_by(
            Project.created_at.desc(),
            Project.id.desc(),
        )
        .offset(offset)
        .limit(limit + 1)
    )
    projects = list(db.scalars(statement).all())
    has_more = len(projects) > limit

    return projects[:limit], has_more


def get_project(
        db: Session,
        project_id:  int,
        user_id: int,
) -> Project | None:
    return db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == user_id,
        )
    )

def update_project(
        db: Session,
        project: Project,
        payload: ProjectUpdate,
) -> Project:
    updates = payload.model_dump(exclude_unset = True)
    for field, value in updates.items():
        setattr(project, field, value)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(project)

    return project

def delete_project(
        db: Session,
        project: Project,
) -> None:
    try:
        db.delete(project)
        db.commit()
    except Exception:
        db.rollback()
        raise