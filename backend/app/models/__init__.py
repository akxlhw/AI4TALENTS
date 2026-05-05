"""
Database models package.
All models are imported here for Alembic to detect them.
"""

from app.domains.shared.models.audit import AuditOperationLog
from app.domains.academic.models.collaboration import Collaboration, WorkAuthor
from app.domains.academic.models.embedding import TalentEmbedding
from app.models.enums import (
    RoleType,
    ScopeType,
    SourceType,
    SyncJobStatus,
    UserRoleType,
    VisibilityStatus,
)
from app.domains.shared.models.iam import (
    FavoriteTalent,
    TalentPool,
    TalentPoolMember,
    UserAccount,
    UserSchoolScope,
)
from app.domains.academic.models.jd_match import JDMatchResult, JDMatchSession
from app.domains.academic.models.raw_data import AuthorTechBelong, RawAuthor, RawInstitution, RawWork
from app.domains.academic.models.school import School, SchoolAlias
from app.domains.academic.models.search import SearchTalentDocument
from app.domains.academic.models.standardized import SchoolNameAlias, StdAuthor, StdSchool
from app.domains.academic.models.statistics import OverviewStatSnapshot, ResearchTopicStats, SchoolStatSnapshot
from app.domains.academic.models.sync import (
    CollectScope,
    CollectStrategy,
    CollectTask,
    DataCorrectionRecord,
    DataPublishRecord,
    DataQualitySummary,
    DataVersion,
    SyncBatch,
)
from app.domains.shared.models.system_config import SystemConfig
from app.domains.academic.models.talent import RoleProfile, SelectedWork, Talent
from app.domains.academic.models.tech_domain import TalentTechTag, TechDirection, TechDomain
from app.domains.academic.models.venue import Venue, VenueSubTask, VenueTechBinding
from app.domains.open_source.models.open_source import (
    OSContribution,
    OSCollectTask,
    OSDeveloper,
    OSEmbedding,
    OSFavourite,
    OSLanguageSkill,
    OSPoolMember,
    OSRawDeveloper,
    OSRepoConfig,
    OSRepoMapping,
    OSRepository,
    OSTalentPool,
)

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
    "TechDomain",
    "TechDirection",
    "TalentTechTag",
    "Collaboration",
    "WorkAuthor",
    # Statistics
    "OverviewStatSnapshot",
    "ResearchTopicStats",
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
    # Open Source (v2.0)
    "OSRepoConfig",
    "OSDeveloper",
    "OSRepository",
    "OSContribution",
    "OSLanguageSkill",
    "OSEmbedding",
    "OSFavourite",
    "OSTalentPool",
    "OSPoolMember",
    "OSCollectTask",
    "OSRawDeveloper",
    "OSRepoMapping",
]
