"""
Repositories module.
"""
from app.repositories.homepage_repository import HomepageRepository
from app.repositories.school_repository import SchoolRepository
from app.repositories.stat_repository import StatisticsRepository
from app.repositories.sync_repository import SyncBatchRepository
from app.repositories.talent_repository import TalentRepository

__all__ = [
    "SyncBatchRepository",
    "StatisticsRepository",
    "SchoolRepository",
    "TalentRepository",
    "HomepageRepository",
]
