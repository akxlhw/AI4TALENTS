"""Raw data layer repositories — backwards-compatible re-export shim.

The implementations live in the raw_data/ package (P2-3 split); this module
keeps the historical import path working.
"""

from app.domains.academic.repositories.raw_data import (  # noqa: F401
    AuthorTechBelongRepository,
    RawAuthorRepository,
    RawInstitutionRepository,
    RawWorkRepository,
)

__all__ = [
    "RawWorkRepository",
    "RawAuthorRepository",
    "RawInstitutionRepository",
    "AuthorTechBelongRepository",
]
