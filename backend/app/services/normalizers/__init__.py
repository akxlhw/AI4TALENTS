"""
Data normalizers for the standardized layer.
"""

from app.services.normalizers.author import AuthorNormalizer
from app.services.normalizers.base import NormalizationResult
from app.services.normalizers.school import SchoolNormalizer
from app.services.normalizers.tech_belong import TechBelongCalculator

__all__ = [
    "NormalizationResult",
    "SchoolNormalizer",
    "AuthorNormalizer",
    "TechBelongCalculator",
]
