"""
Embedding domain service.

Encapsulates EmbeddingRepository, EmbeddingService, and LLMGateway usage
so that Endpoints do not import them directly.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.domains.academic.repositories.embedding_repository import EmbeddingRepository
from app.domains.academic.services.embedding.embedding_service import EmbeddingService
from app.domains.shared.services.config_service import ConfigService
from app.domains.shared.services.llm import LLMGateway

logger = logging.getLogger(__name__)


class EmbeddingDomainService:
    """Domain service for embedding operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = EmbeddingRepository(session)

    async def get_embedding_status(self) -> dict:
        """Get embedding generation status statistics."""
        return await self.repo.get_embedding_status()

    async def get_visible_talent_ids(self) -> list[int]:
        """Get IDs of all visible talents."""
        return await self.repo.get_visible_talent_ids()

    @staticmethod
    async def run_background_generation(
        force: bool,
        batch_size: int,
        vector_types: list[str],
        progress_tracker: dict,
    ) -> None:
        """Run embedding generation in background using a new session."""
        try:
            await EmbeddingDomainService._do_run_background_generation(
                force, batch_size, vector_types, progress_tracker
            )
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            progress_tracker["status"] = "error"
            progress_tracker["error_message"] = str(e)
            progress_tracker["completed_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    @staticmethod
    async def _do_run_background_generation(
        force: bool,
        batch_size: int,
        vector_types: list[str],
        progress_tracker: dict,
    ) -> None:
        async with AsyncSessionLocal() as session:
            config_service = ConfigService(session)
            llm_config = await config_service.get_llm_config()

            if not llm_config.embedding_enabled:
                progress_tracker["status"] = "error"
                progress_tracker["error_message"] = "嵌入模型未启用。请先启用嵌入模型功能。"
                return

            if not llm_config.embedding_model:
                progress_tracker["status"] = "error"
                progress_tracker["error_message"] = "嵌入模型名称未配置。请配置嵌入模型名称。"
                return

            if not llm_config.embedding_api_base:
                progress_tracker["status"] = "error"
                progress_tracker["error_message"] = (
                    "嵌入 API 地址未配置。请配置嵌入模型的 API 地址。"
                )
                return

            logger.info(
                f"Creating LLMGateway with embedding_api_base={llm_config.embedding_api_base}, "
                f"embedding_model={llm_config.embedding_model}"
            )

            llm_gateway = LLMGateway(
                api_key=llm_config.api_key,
                api_base=llm_config.api_base,
                model=llm_config.model,
                embedding_model=llm_config.embedding_model,
                embedding_api_base=llm_config.embedding_api_base,
                embedding_api_key=llm_config.embedding_api_key,
                timeout=llm_config.timeout or settings.LLM_TIMEOUT,
                api_format=llm_config.api_format,
                embedding_api_format=llm_config.embedding_api_format,
            )

            logger.info(
                f"LLMGateway api_format={llm_gateway.api_format}, "
                f"embedding_api_format={llm_gateway.embedding_api_format}"
            )

            repo = EmbeddingRepository(session)
            talent_ids = await repo.get_visible_talent_ids()

            embedding_model = llm_config.embedding_model
            progress_tracker["total"] = len(talent_ids) * len(vector_types)

            if not talent_ids:
                progress_tracker["status"] = "completed"
                progress_tracker["completed_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
                return

            embed_service = EmbeddingService(
                session=session,
                llm_gateway=llm_gateway,
                rate_limit_delay=1.0,
                model_name=embedding_model,
                dimension=llm_config.embedding_dimension,
            )

            processed = 0
            failed = 0
            if llm_gateway.embedding_api_format == "minimax":
                actual_batch_size = min(batch_size, 16)
            else:
                actual_batch_size = min(batch_size, 64)

            for i in range(0, len(talent_ids), actual_batch_size):
                if progress_tracker["status"] == "cancelled":
                    logger.info("Embedding generation cancelled")
                    return

                batch = talent_ids[i : i + actual_batch_size]

                try:
                    stats = await embed_service.batch_generate_embeddings(
                        talent_ids=batch,
                        batch_size=actual_batch_size,
                        force_regenerate=force,
                        vector_types=vector_types,
                    )
                    processed += stats.get("processed", 0)
                    failed += stats.get("failed", 0)

                    progress_tracker["processed"] = processed
                    progress_tracker["failed"] = failed
                    logger.info(
                        f"Progress: {processed}/{progress_tracker['total']} processed, "
                        f"{failed} failed"
                    )

                except Exception as e:
                    logger.error(f"Batch {i // actual_batch_size + 1} failed: {e}")
                    failed += len(batch) * len(vector_types)
                    progress_tracker["failed"] = failed

            progress_tracker["status"] = "completed"
            progress_tracker["completed_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            logger.info(
                f"Embedding generation completed: processed={processed}, failed={failed}"
            )
