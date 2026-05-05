"""
Repositories module.
"""

from app.domains.academic.repositories.homepage_repository import HomepageRepository
from app.domains.academic.repositories.school_repository import SchoolRepository
from app.domains.academic.repositories.stat_repository import StatisticsRepository
from app.domains.academic.repositories.sync_repository import SyncBatchRepository
from app.domains.academic.repositories.talent_repository import TalentRepository

__all__ = [
    "SyncBatchRepository",
    "StatisticsRepository",
    "SchoolRepository",
    "TalentRepository",
    "HomepageRepository",
]
