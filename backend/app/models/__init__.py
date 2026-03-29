"""
Database models package.
All models are imported here for Alembic to detect them.
"""
from app.models.enums import RoleType, VisibilityStatus, UserRoleType, SyncJobStatus, SourceType, ScopeType
from app.models.country import Country
from app.models.school import School, SchoolAlias
from app.models.talent import Talent, RoleProfile, SelectedWork
from app.models.tech_element import TechElement, TechDirection, TalentTechTag
from app.models.collaboration import Collaboration, WorkAuthor
from app.models.statistics import OverviewStatSnapshot, SchoolStatSnapshot
from app.models.iam import UserAccount, UserSchoolScope, FavoriteTalent, TalentPool, TalentPoolMember
from app.models.sync import (
    SyncBatch, CollectScope, CollectStrategy, CollectTask,
    DataVersion, DataPublishRecord, DataCorrectionRecord, DataQualitySummary,
)
from app.models.venue import Venue, VenueTechBinding, VenueSubTask
from app.models.raw_data import RawWork, RawAuthor, RawInstitution, AuthorTechBelong
from app.models.standardized import StdAuthor, StdSchool, SchoolNameAlias
from app.models.search import SearchTalentDocument
from app.models.audit import AuditOperationLog

__all__ = [
    # Enums
    "RoleType",
    "VisibilityStatus",
    "UserRoleType",
    "SyncJobStatus",
    "SourceType",
    "ScopeType",
    # Core models
    "Country",
    "School",
    "SchoolAlias",
    "Talent",
    "RoleProfile",
    "SelectedWork",
    "TechElement",
    "TechDirection",
    "TalentTechTag",
    "Collaboration",
    "WorkAuthor",
    # Statistics
    "OverviewStatSnapshot",
    "SchoolStatSnapshot",
    # IAM
    "UserAccount",
    "UserSchoolScope",
    "FavoriteTalent",
    "TalentPool",
    "TalentPoolMember",
    # Sync
    "SyncBatch",
    "CollectScope",
    "CollectStrategy",
    "CollectTask",
    "DataVersion",
    "DataPublishRecord",
    "DataCorrectionRecord",
    "DataQualitySummary",
    # Venue Config
    "Venue",
    "VenueTechBinding",
    "VenueSubTask",
    # Raw Data Layer
    "RawWork",
    "RawAuthor",
    "RawInstitution",
    "AuthorTechBelong",
    # Standardized Layer
    "StdAuthor",
    "StdSchool",
    "SchoolNameAlias",
    # Search
    "SearchTalentDocument",
    # Audit
    "AuditOperationLog",
]
