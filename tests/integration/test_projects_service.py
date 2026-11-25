import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.project import Project
from app.models.task import Task
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.user import UserRegister
from app.services.auth import register_user
from app.services.projects import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)


def create_test_user(db_session, email: str):
    registration = UserRegister(
        email=email,
        password="test-password-12345",
        display_name="Test User",
    )
    return register_user(db_session, registration)


def test_create_project_assigns_owner(db_session):
    user = create_test_user(db_session, "owner@example.com")

    payload = ProjectCreate(
        name="My Indie Game",
        description="A small adventure game.",
    )

    project = create_project(db_session, payload, user.id)

    assert project.id is not None
    assert project.owner_id == user.id
    assert project.name == "My Indie Game"
    assert project.description == "A small adventure game."


def test_list_projects_returns_only_owner_projects(db_session):
    owner = create_test_user(db_session, "owner@example.com")
    another_user = create_test_user(db_session, "another@example.com")

    own_project = create_project(
        db_session,
        ProjectCreate(name="My Project"),
        owner.id,
    )

    create_project(
        db_session,
        ProjectCreate(name="Someone Else's Project"),
        another_user.id,
    )

    projects, has_more = list_projects(
        db_session,
        owner.id,
        limit=20,
        offset=0,
    )

    assert [project.id for project in projects] == [own_project.id]
    assert has_more is False


def test_list_projects_paginates_and_orders_stably(db_session):
    user = create_test_user(db_session, "owner@example.com")

    created_projects = []

    for name in ["First", "Second", "Third"]:
        project = create_project(
            db_session,
            ProjectCreate(name=name),
            user.id,
        )
        created_projects.append(project)

    first_page, has_more = list_projects(
        db_session,
        user.id,
        limit=2,
        offset=0,
    )

    second_page, second_has_more = list_projects(
        db_session,
        user.id,
        limit=2,
        offset=2,
    )

    expected_ids = [project.id for project in reversed(created_projects)]

    assert [project.id for project in first_page] == expected_ids[:2]
    assert [project.id for project in second_page] == expected_ids[2:]
    assert has_more is True
    assert second_has_more is False


def test_get_project_returns_owned_project(db_session):
    user = create_test_user(db_session, "owner@example.com")

    project = create_project(
        db_session,
        ProjectCreate(name="My Project"),
        user.id,
    )

    result = get_project(db_session, project.id, user.id)

    assert result is not None
    assert result.id == project.id


def test_get_project_does_not_return_another_users_project(db_session):
    owner = create_test_user(db_session, "owner@example.com")
    another_user = create_test_user(db_session, "another@example.com")

    project = create_project(
        db_session,
        ProjectCreate(name="Private Project"),
        owner.id,
    )

    result = get_project(db_session, project.id, another_user.id)

    assert result is None


def test_update_project_changes_only_supplied_fields(db_session):
    user = create_test_user(db_session, "owner@example.com")

    project = create_project(
        db_session,
        ProjectCreate(
            name="Original Name",
            description="Original description",
        ),
        user.id,
    )

    updated = update_project(
        db_session,
        project,
        ProjectUpdate(name="Updated Name"),
    )

    assert updated.name == "Updated Name"
    assert updated.description == "Original description"


def test_update_project_can_clear_description(db_session):
    user = create_test_user(db_session, "owner@example.com")

    project = create_project(
        db_session,
        ProjectCreate(
            name="My Project",
            description="Description to clear",
        ),
        user.id,
    )

    updated = update_project(
        db_session,
        project,
        ProjectUpdate(description=None),
    )

    assert updated.description is None


def test_delete_project(db_session):
    user = create_test_user(db_session, "owner@example.com")

    project = create_project(
        db_session,
        ProjectCreate(name="Project to delete"),
        user.id,
    )

    project_id = project.id

    delete_project(db_session, project)

    result = db_session.get(Project, project_id)

    assert result is None

def test_delete_project_cascades_to_tasks(db_session):
    user = create_test_user(db_session, "owner@example.com")

    project = create_project(
        db_session,
        ProjectCreate(name="Project with tasks"),
        user.id,
    )

    task = Task(
        project_id=project.id,
        title="Implement player movement",
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    task_id = task.id
    project_id = project.id

    delete_project(db_session, project)

    deleted_project = db_session.get(Project, project_id)
    deleted_task = db_session.get(Task, task_id)

    assert deleted_project is None
    assert deleted_task is None

def test_failed_project_insert_rolls_back_transaction(db_session):
    user = create_test_user(db_session, "owner@example.com")

    invalid_project = Project(
        owner_id=user.id,
        name="   ",
    )

    db_session.add(invalid_project)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()

    projects = db_session.scalars(
        select(Project).where(Project.owner_id == user.id)
    ).all()

    assert projects == []

    # The session must remain usable after rollback.
    valid_project = create_project(
        db_session,
        ProjectCreate(name="Valid Project"),
        user.id,
    )

    assert valid_project.id is not None
    assert valid_project.name == "Valid Project"