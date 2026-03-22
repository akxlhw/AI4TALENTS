"""
Enumeration types for the application.
"""
import enum


class RoleType(str, enum.Enum):
    """Talent role type enumeration."""
    PROFESSOR = "professor"
    TEACHING_RESEARCH = "teaching_research"
    STUDENT = "student"
    GRADUATED = "graduated"
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
