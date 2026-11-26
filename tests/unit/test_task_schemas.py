import pytest
from pydantic import ValidationError

from app.schemas.task import TaskCreate, TaskUpdate


def test_create_normalizes_title():
    task = TaskCreate(title="  Implement movement  ")

    assert task.title == "Implement movement"


def test_create_uses_default_status():
    task = TaskCreate(title="Implement movement")

    assert task.status == "todo"


def test_create_allows_null_description():
    task = TaskCreate(
        title="Implement movement",
        description=None,
    )

    assert task.description is None


def test_create_rejects_missing_title():
    with pytest.raises(ValidationError):
        TaskCreate()


def test_create_rejects_null_title():
    with pytest.raises(ValidationError):
        TaskCreate(title=None)


def test_create_rejects_whitespace_title():
    with pytest.raises(ValidationError):
        TaskCreate(title="   ")


def test_create_rejects_title_over_200_characters():
    with pytest.raises(ValidationError):
        TaskCreate(title="a" * 201)


def test_create_rejects_description_over_10000_characters():
    with pytest.raises(ValidationError):
        TaskCreate(
            title="Valid title",
            description="a" * 10001,
        )


def test_create_rejects_invalid_status():
    with pytest.raises(ValidationError):
        TaskCreate(title="Valid title", status="blocked")


def test_create_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        TaskCreate(title="Valid title", project_id=1)


def test_update_allows_omitted_fields():
    task = TaskUpdate(title="Updated title")

    assert task.title == "Updated title"
    assert task.description is None
    assert task.status is None


def test_update_allows_null_description():
    task = TaskUpdate(description=None)

    assert task.description is None


def test_update_rejects_empty_payload():
    with pytest.raises(ValidationError):
        TaskUpdate()


def test_update_rejects_null_title():
    with pytest.raises(ValidationError):
        TaskUpdate(title=None)


def test_update_rejects_null_status():
    with pytest.raises(ValidationError):
        TaskUpdate(status=None)


def test_update_rejects_whitespace_title():
    with pytest.raises(ValidationError):
        TaskUpdate(title="   ")


def test_update_rejects_invalid_status():
    with pytest.raises(ValidationError):
        TaskUpdate(status="blocked")


def test_update_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        TaskUpdate(project_id=1)
