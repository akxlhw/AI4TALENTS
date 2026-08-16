"""Raw data repositories — split from the former monolithic
raw_data_repository.py (P2-3 refactor). Import surface unchanged."""

from app.domains.academic.repositories.raw_data.author_tech_belong import (
    AuthorTechBelongRepository,
)
from app.domains.academic.repositories.raw_data.raw_author import RawAuthorRepository
from app.domains.academic.repositories.raw_data.raw_institution import (
    RawInstitutionRepository,
)
from app.domains.academic.repositories.raw_data.raw_work import RawWorkRepository

__all__ = [
    "RawWorkRepository",
    "RawAuthorRepository",
    "RawInstitutionRepository",
    "AuthorTechBelongRepository",
]
