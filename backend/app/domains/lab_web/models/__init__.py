"""lab_web ORM models."""

from app.domains.lab_web.models.lab_web import (
    LWCollectTask,
    LWLabRegistry,
    LWRawPerson,
)

__all__ = ["LWLabRegistry", "LWRawPerson", "LWCollectTask"]
