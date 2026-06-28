"""LWRepository exports."""

from app.domains.lab_web.repositories.lab_web.core import LWRepository
from app.domains.lab_web.repositories.lab_web.site import LWSiteRepository

__all__ = ["LWRepository", "LWSiteRepository"]
