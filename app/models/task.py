from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project

class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "length(trim(title)) > 0",
            name = "title_not_blank",
        ),
        CheckConstraint(
            "status IN ('todo', 'in_progress', 'done')",
            name="valid_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key = True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete = "CASCADE"),
        nullable = False,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable = False
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable = True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable = False,
        server_default = "todo",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    project: Mapped["Project"] = relationship(
        back_populates = "tasks",
    )