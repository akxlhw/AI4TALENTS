"""
Repositories module.
"""
from app.repositories.sync_repository import SyncBatchRepository
from app.repositories.stat_repository import StatisticsRepository
from app.repositories.country_repository import CountryRepository
from app.repositories.school_repository import SchoolRepository
from app.repositories.talent_repository import TalentRepository
from app.repositories.homepage_repository import HomepageRepository

__all__ = [
    "SyncBatchRepository",
    "StatisticsRepository",
    "CountryRepository",
    "SchoolRepository",
    "TalentRepository",
    "HomepageRepository",
]
