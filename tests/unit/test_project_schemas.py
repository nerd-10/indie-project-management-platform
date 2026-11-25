import pytest
from pydantic import ValidationError

from app.schemas.project import ProjectCreate, ProjectUpdate


def test_create_normalizes_name():
    project = ProjectCreate(name="  My Game  ")
    assert project.name == "My Game"


def test_patch_allows_omitted_name():
    project = ProjectUpdate(description="Updated")
    assert project.name is None


def test_patch_allows_null_description():
    project = ProjectUpdate(description=None)
    assert project.description is None


def test_patch_rejects_null_name():
    with pytest.raises(ValidationError):
        ProjectUpdate(name=None)


def test_patch_rejects_empty_payload():
    with pytest.raises(ValidationError):
        ProjectUpdate()


def test_patch_rejects_whitespace_name():
    with pytest.raises(ValidationError):
        ProjectUpdate(name="   ")


def test_patch_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        ProjectUpdate(owner_id=1)

def test_project_create_rejects_missing_name():
    with pytest.raises(ValidationError):
        ProjectCreate(description="A project description")


def test_project_create_rejects_null_name():
    with pytest.raises(ValidationError):
        ProjectCreate(name=None)

def test_project_create_rejects_whitespace_name():
    with pytest.raises(ValidationError):
        ProjectCreate(name="   ")