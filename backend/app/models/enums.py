"""
Enumeration types for the application.
"""
import enum


class RoleType(str, enum.Enum):
    """Talent role type enumeration.

    Unified role types for academic talent identification.
    - PROFESSOR: 教授/研究员 (h_index >= 25 or high citation count)
    - STUDENT: 在读学生 (works <= 8 and low citations)
    - GRADUATE: 毕业/早期研究者 (8 < works < 30, transitioning)
    - UNKNOWN: 未知 (insufficient data)
    """
    PROFESSOR = "professor"
    STUDENT = "student"
    GRADUATE = "graduate"
    UNKNOWN = "unknown"


class VisibilityStatus(str, enum.Enum):
    """Visibility status enumeration."""
    ACTIVE = "active"
    PENDING = "pending"
    HIDDEN = "hidden"


class UserRoleType(str, enum.Enum):
    """User role type enumeration."""
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    USER = "user"


class SyncJobStatus(str, enum.Enum):
    """Sync job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class SourceType(str, enum.Enum):
    """Data source type enumeration."""
    OPENALEX = "openalex"
    MANUAL = "manual"
    IMPORT = "import"


class ScopeType(str, enum.Enum):
    """Permission scope type enumeration."""
    SCHOOL = "school"
    COUNTRY = "country"
    ALL = "all"
