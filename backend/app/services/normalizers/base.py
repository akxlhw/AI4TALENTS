"""
Base classes and data structures for normalizers.
"""
from dataclasses import dataclass


@dataclass
class NormalizationResult:
    """Result of a normalization operation"""
    total: int = 0
    processed: int = 0
    created: int = 0
    updated: int = 0
    failed: int = 0
    pending_schools: int = 0
