"""
Open Source Repository - core facade.

Aggregates per-responsibility query mixins (split from the original monolith)
so the public `OpenSourceCoreRepository` interface stays unchanged.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.repositories.open_source.collect_tasks import CollectTasksMixin
from app.domains.open_source.repositories.open_source.developers import DevelopersMixin
from app.domains.open_source.repositories.open_source.favourites import FavouritesMixin
from app.domains.open_source.repositories.open_source.pools import PoolsMixin
from app.domains.open_source.repositories.open_source.purge import PurgeMixin
from app.domains.open_source.repositories.open_source.repo_configs import RepoConfigsMixin


class OpenSourceCoreRepository(
    DevelopersMixin,
    FavouritesMixin,
    PoolsMixin,
    CollectTasksMixin,
    RepoConfigsMixin,
    PurgeMixin,
):
    """Core CRUD operations for open-source talent."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
