from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra = "forbid")
    name: str = Field(
        min_length = 1, 
        max_length = 150,
        )
    description: str| None = None

    @field_validator("name", mode = "before")
    @classmethod
    def normalize_name(cls, value:str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra = "forbid")
    name: str|None = Field(
        default=None,
        min_length = 1, 
        max_length = 150,
        )
    description: str| None = None

    @field_validator("name", mode = "before")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            return value.strip()
        return value
    @model_validator(mode="after")
    def validate_patch(self) -> "ProjectUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Project name cannot be null.")
        
        return self

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str|None
    created_at: datetime
    updated_at: datetime

class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    limit: int
    offset: int
    has_more: bool