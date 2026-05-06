"""
Open Source Domain — Public Service exports.

Endpoints should ONLY import from this package or specific service modules.
Never import Repository, Collector, or low-level clients from this domain.
"""

from app.domains.open_source.services.open_source_service import OpenSourceService

__all__ = ["OpenSourceService"]
