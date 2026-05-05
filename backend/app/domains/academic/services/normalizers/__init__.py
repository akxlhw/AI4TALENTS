"""
Data normalizers for the standardized layer.
"""

from app.domains.academic.services.normalizers.author import AuthorNormalizer
from app.domains.academic.services.normalizers.base import NormalizationResult
from app.domains.academic.services.normalizers.school import SchoolNormalizer
from app.domains.academic.services.normalizers.tech_belong import TechBelongCalculator

__all__ = [
    "NormalizationResult",
    "SchoolNormalizer",
    "AuthorNormalizer",
    "TechBelongCalculator",
]
