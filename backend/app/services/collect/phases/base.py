"""Base class and shared context for collection phase handlers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync import CollectTask
from app.services.collect.progress_tracker import ProgressTracker
from app.services.common.progress import CollectionProgress


@dataclass
class PhaseContext:
    """Shared context passed between phase handlers during task execution."""

    task: CollectTask
    progress: CollectionProgress
    # Intermediate results storage between phases
    new_talents: list[dict] = field(default_factory=list)
    estimated_total: int = 0


class PhaseHandler(ABC):
    """Abstract base class for collection phase handlers.

    Each phase handler is responsible for a single, well-defined step
    in the collection pipeline. Handlers receive a shared :class:`PhaseContext`
    and may read from or write to it to communicate with other phases.
    """

    def __init__(self, session: AsyncSession, progress_tracker: ProgressTracker) -> None:
        self.session = session
        self.progress_tracker = progress_tracker

    @property
    @abstractmethod
    def phase_name(self) -> str:
        """Human-readable phase name shown in progress tracking."""

    @property
    @abstractmethod
    def phase_progress(self) -> int:
        """Target progress percentage (0-100) for this phase."""

    @abstractmethod
    async def execute(self, context: PhaseContext) -> Any:
        """Execute this phase.

        Args:
            context: Shared phase context containing the task, progress object,
                and any intermediate results produced by earlier phases.

        Returns:
            Optional result to be stored in ``context`` or used by the caller.
        """
