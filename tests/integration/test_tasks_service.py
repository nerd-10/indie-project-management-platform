import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.task import Task
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.user import UserRegister
from app.services.auth import register_user
from app.services.projects import create_project
from app.services.tasks import (
    create_task,
    delete_task,
    get_task,
    list_tasks,
    update_task,
)


def create_test_user(db_session, email: str):
    registration = UserRegister(
        email=email,
        password="test-password-12345",
        display_name="Test User",
    )
    return register_user(db_session, registration)


def create_test_project(db_session, user, name="Test Project"):
    return create_project(
        db_session,
        ProjectCreate(name=name),
        user.id,
    )


def test_create_task_assigns_project_and_default_status(db_session):
    user = create_test_user(db_session, "task-owner@example.com")
    project = create_test_project(db_session, user)

    task = create_task(
        db_session,
        project,
        TaskCreate(title="Implement player movement"),
    )

    assert task.id is not None
    assert task.project_id == project.id
    assert task.title == "Implement player movement"
    assert task.status == "todo"
    assert task.description is None


def test_list_tasks_returns_only_project_tasks(db_session):
    user = create_test_user(db_session, "list-owner@example.com")
    project_one = create_test_project(db_session, user, "Project One")
    project_two = create_test_project(db_session, user, "Project Two")

    task_one = create_task(
        db_session,
        project_one,
        TaskCreate(title="Task One"),
    )
    create_task(
        db_session,
        project_two,
        TaskCreate(title="Task Two"),
    )

    tasks, has_more = list_tasks(
        db_session,
        project_one.id,
        limit=20,
        offset=0,
    )

    assert [task.id for task in tasks] == [task_one.id]
    assert has_more is False


def test_list_tasks_paginates_and_orders_stably(db_session):
    user = create_test_user(db_session, "pagination-owner@example.com")
    project = create_test_project(db_session, user)

    created_tasks = []

    for title in ["First", "Second", "Third"]:
        task = create_task(
            db_session,
            project,
            TaskCreate(title=title),
        )
        created_tasks.append(task)

    first_page, has_more = list_tasks(
        db_session,
        project.id,
        limit=2,
        offset=0,
    )

    second_page, second_has_more = list_tasks(
        db_session,
        project.id,
        limit=2,
        offset=2,
    )

    expected_ids = [task.id for task in reversed(created_tasks)]

    assert [task.id for task in first_page] == expected_ids[:2]
    assert [task.id for task in second_page] == expected_ids[2:]
    assert has_more is True
    assert second_has_more is False


def test_get_task_returns_task_from_correct_project(db_session):
    user = create_test_user(db_session, "retrieve-owner@example.com")
    project = create_test_project(db_session, user)

    task = create_task(
        db_session,
        project,
        TaskCreate(title="Find this task"),
    )

    result = get_task(db_session, project.id, task.id)

    assert result is not None
    assert result.id == task.id


def test_get_task_rejects_incorrect_project_id(db_session):
    user = create_test_user(db_session, "mismatch-owner@example.com")
    project_one = create_test_project(db_session, user, "Project One")
    project_two = create_test_project(db_session, user, "Project Two")

    task = create_task(
        db_session,
        project_one,
        TaskCreate(title="Private task"),
    )

    result = get_task(db_session, project_two.id, task.id)

    assert result is None


def test_get_task_returns_none_for_nonexistent_task(db_session):
    user = create_test_user(db_session, "missing-owner@example.com")
    project = create_test_project(db_session, user)

    result = get_task(db_session, project.id, 999999999)

    assert result is None


def test_update_task_changes_only_supplied_fields(db_session):
    user = create_test_user(db_session, "update-owner@example.com")
    project = create_test_project(db_session, user)

    task = create_task(
        db_session,
        project,
        TaskCreate(
            title="Original title",
            description="Original description",
        ),
    )

    updated = update_task(
        db_session,
        task,
        TaskUpdate(title="Updated title"),
    )

    assert updated.title == "Updated title"
    assert updated.description == "Original description"
    assert updated.status == "todo"


def test_update_task_can_clear_description(db_session):
    user = create_test_user(db_session, "clear-owner@example.com")
    project = create_test_project(db_session, user)

    task = create_task(
        db_session,
        project,
        TaskCreate(
            title="Task",
            description="Description to clear",
        ),
    )

    updated = update_task(
        db_session,
        task,
        TaskUpdate(description=None),
    )

    assert updated.description is None


def test_update_task_can_change_status(db_session):
    user = create_test_user(db_session, "status-owner@example.com")
    project = create_test_project(db_session, user)

    task = create_task(
        db_session,
        project,
        TaskCreate(title="Task"),
    )

    updated = update_task(
        db_session,
        task,
        TaskUpdate(status="in_progress"),
    )

    assert updated.status == "in_progress"


def test_delete_task(db_session):
    user = create_test_user(db_session, "delete-owner@example.com")
    project = create_test_project(db_session, user)

    task = create_task(
        db_session,
        project,
        TaskCreate(title="Task to delete"),
    )

    task_id = task.id

    delete_task(db_session, task)

    assert db_session.get(Task, task_id) is None


def test_failed_task_insert_rolls_back_transaction(db_session):
    user = create_test_user(db_session, "rollback-owner@example.com")
    project = create_test_project(db_session, user)

    invalid_task = Task(
        project_id=project.id,
        title="   ",
    )

    db_session.add(invalid_task)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()

    tasks = db_session.scalars(
        select(Task).where(Task.project_id == project.id)
    ).all()

    assert tasks == []

    valid_task = create_task(
        db_session,
        project,
        TaskCreate(title="Valid task"),
    )

    assert valid_task.id is not None
