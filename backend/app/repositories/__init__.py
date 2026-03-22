"""
Repositories module.
"""
from app.repositories.sync_repository import SyncBatchRepository, RawSourceRecordRepository
from app.repositories.stat_repository import StatisticsRepository
from app.repositories.country_repository import CountryRepository
from app.repositories.school_repository import SchoolRepository
from app.repositories.talent_repository import TalentRepository

__all__ = [
    "SyncBatchRepository",
    "RawSourceRecordRepository",
    "StatisticsRepository",
    "CountryRepository",
    "SchoolRepository",
    "TalentRepository",
]
