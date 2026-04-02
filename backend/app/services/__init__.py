"""
Services module.

This module provides services for data collection, normalization, and synchronization.

## Module Structure

- common/: Shared utilities and progress tracking
- normalizers/: Data normalization services
- collect/: Collection pipeline services
- sync/: Serving layer synchronization services

## Usage

For backward compatibility, you can continue using:
- UnifiedCollectService (deprecated, use CollectionOrchestrator)
- ServingLayerSync (deprecated, use ServingLayerOrchestrator)

For new code, prefer using the specialized services directly:
- CollectionOrchestrator for collection pipeline
- ServingLayerOrchestrator for sync operations
"""
# Legacy exports (backward compatible)
# Collection services
from app.services.collect import (
    CollectionOrchestrator,
    ProgressTracker,
    TaskCreationService,
    VenueSubTaskExecutor,
)

# Common utilities
from app.services.common import (
    OPENALEX_API_BASE,
    BaseProgress,
    CollectionProgress,
    FetchProgress,
    extract_short_id,
)

# Data fetchers (kept for backward compatibility)
from app.services.data_fetchers import (
    AuthorFetcher,
    InstitutionFetcher,
    OpenAlexClient,
    WorkFetcher,
)

# Normalizers
from app.services.normalizers import (
    AuthorNormalizer,
    NormalizationResult,
    SchoolNormalizer,
    TechBelongCalculator,
)
from app.services.role_identifier import RoleIdentificationResult, RoleIdentifier
from app.services.serving_layer_sync import ServingLayerSync

# Sync services
from app.services.sync import (
    AuthorSyncService,
    SchoolSyncService,
    ServingLayerOrchestrator,
    TechTagSyncService,
)

# Talent service
from app.services.talent_service import TalentService
from app.services.unified_collect_service import CollectMode, UnifiedCollectService

__all__ = [
    # Legacy (deprecated)
    "UnifiedCollectService",
    "CollectMode",
    "ServingLayerSync",
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
