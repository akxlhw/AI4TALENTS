"""
Database models package.
All models are imported here for Alembic to detect them.
"""
from app.models.audit import AuditOperationLog
from app.models.collaboration import Collaboration, WorkAuthor
from app.models.enums import (
    RoleType,
    ScopeType,
    SourceType,
    SyncJobStatus,
    UserRoleType,
    VisibilityStatus,
)
from app.models.iam import (
    FavoriteTalent,
    TalentPool,
    TalentPoolMember,
    UserAccount,
    UserSchoolScope,
)
from app.models.raw_data import AuthorTechBelong, RawAuthor, RawInstitution, RawWork
from app.models.school import School, SchoolAlias
from app.models.search import SearchTalentDocument
from app.models.standardized import SchoolNameAlias, StdAuthor, StdSchool
from app.models.statistics import OverviewStatSnapshot, SchoolStatSnapshot
from app.models.sync import (
    CollectScope,
    CollectStrategy,
    CollectTask,
    DataCorrectionRecord,
    DataPublishRecord,
    DataQualitySummary,
    DataVersion,
    SyncBatch,
)
from app.models.talent import RoleProfile, SelectedWork, Talent
from app.models.tech_element import TalentTechTag, TechDirection, TechElement
from app.models.venue import Venue, VenueSubTask, VenueTechBinding
from app.models.embedding import TalentEmbedding
from app.models.jd_match import JDMatchSession, JDMatchResult
from app.models.system_config import SystemConfig

__all__ = [
    # Enums
    "RoleType",
    "VisibilityStatus",
    "UserRoleType",
    "SyncJobStatus",
    "SourceType",
    "ScopeType",
    # Core models
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
    # Embedding (v1.4)
    "TalentEmbedding",
    # JD Match (v1.4)
    "JDMatchSession",
    "JDMatchResult",
    # System Config (v1.4)
    "SystemConfig",
    # Audit
    "AuditOperationLog",
]
