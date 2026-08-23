"""
Open Source Domain — Public Service exports.

Endpoints should ONLY import from specific service modules, e.g.::

    from app.domains.open_source.services.open_source_service import OpenSourceService

Never import Repository, Collector, or low-level clients from this domain.

This package intentionally contains no imports: an eager re-export here made
every submodule import execute the whole service graph first, which is both a
startup cost and a circular-import hazard (2026-08 audit finding).
"""
