"""
Services module.

This module provides services for data collection, normalization, and synchronization.

## Module Structure

- common/: Shared utilities and progress tracking
- normalizers/: Data normalization services
- collect/: Collection pipeline services
- sync/: Serving layer synchronization services

## Usage

For new code, prefer using the specialized services directly:
- CollectionOrchestrator for collection pipeline
- ServingLayerOrchestrator for sync operations
"""

# Legacy exports (backward compatible)
# Collection services
from app.domains.academic.services.collect import (
    CollectionOrchestrator,
    ProgressTracker,
    TaskCreationService,
    VenueSubTaskExecutor,
)

# Common utilities
from app.domains.academic.services.common import (
    OPENALEX_API_BASE,
    BaseProgress,
    CollectionProgress,
    FetchProgress,
    extract_short_id,
)

# Data fetchers (kept for backward compatibility)
from app.domains.academic.services.data_fetchers import (
    AuthorFetcher,
    InstitutionFetcher,
    OpenAlexClient,
    WorkFetcher,
)

# Normalizers
from app.domains.academic.services.normalizers import (
    AuthorNormalizer,
    NormalizationResult,
    SchoolNormalizer,
    TechBelongCalculator,
)
from app.domains.academic.services.role_identifier import RoleIdentificationResult, RoleIdentifier

# Sync services
from app.domains.academic.services.sync import (
    AuthorSyncService,
    SchoolSyncService,
    ServingLayerOrchestrator,
    TechTagSyncService,
)

# Talent service
from app.domains.academic.services.talent_service import TalentService

__all__ = [
    # Utilities
    "RoleIdentifier",
    "RoleIdentificationResult",
    # Common
    "extract_short_id",
    "OPENALEX_API_BASE",
    "CollectionProgress",
    "BaseProgress",
    "FetchProgress",
    # Normalizers
    "NormalizationResult",
    "SchoolNormalizer",
    "AuthorNormalizer",
    "TechBelongCalculator",
    # Collection
    "ProgressTracker",
    "TaskCreationService",
    "VenueSubTaskExecutor",
    "CollectionOrchestrator",
    # Sync
    "AuthorSyncService",
    "SchoolSyncService",
    "TechTagSyncService",
    "ServingLayerOrchestrator",
    # Fetchers
    "WorkFetcher",
    "AuthorFetcher",
    "InstitutionFetcher",
    "OpenAlexClient",
    # Services
    "TalentService",
]
