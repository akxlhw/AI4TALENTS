"""
Open Source Embedding Service - 开源人才嵌入向量管理

从 OpenSourceService 拆分出的嵌入向量相关业务逻辑，包括：
- 嵌入状态查询
- 批量/单条嵌入生成
- 后台嵌入生成任务
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.domains.open_source.repositories.open_source import OpenSourceRepository

logger = logging.getLogger(__name__)


class OSEmbeddingService:
    """
    开源人才嵌入向量服务 - 封装嵌入向量相关的业务逻辑

    职责：
    - 嵌入状态查询
    - 批量/单条嵌入生成触发
    - 后台嵌入生成任务执行
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OpenSourceRepository(session)

    # ============= Embedding =============

    async def get_embedding_status(self) -> dict[str, int]:
        """
        获取嵌入向量状态

        Returns:
            dict: 包含 total_developers, embedded_count, pending_count
        """
        return await self.repo.get_embedding_status()

    async def get_embedding_status_with_config(self) -> dict[str, Any]:
        """Return embedding status enriched with LLM config."""
        from app.domains.shared.services.config_service import ConfigService

        config_service = ConfigService(self.session)
        llm_config = await config_service.get_llm_config()
        status = await self.repo.get_embedding_status()
        total = status["total_developers"] or 0
        embedded = status["embedded_count"] or 0
        progress = (embedded / total * 100) if total > 0 else 0
        return {
            "total_developers": total,
            "embedded_count": embedded,
            "pending_count": status["pending_count"],
            "progress_percent": round(progress, 1),
            "dimension": llm_config.embedding_dimension,
            "model_name": llm_config.embedding_model or "unknown",
        }

    async def trigger_batch_embedding(self, batch_size: int, force: bool) -> int:
        """Validate embedding config and return number of developers to process.

        Raises:
            ValueError: If embedding is not configured or no developers exist.
        """
        from app.domains.shared.services.config_service import ConfigService

        config_service = ConfigService(self.session)
        llm_config = await config_service.get_llm_config()

        if not llm_config.embedding_enabled:
            raise ValueError("嵌入模型未启用")
        if not llm_config.embedding_model:
            raise ValueError("嵌入模型未配置")
        if not llm_config.embedding_api_base:
            raise ValueError("嵌入 API 地址未配置")

        dev_ids = await self.repo.get_visible_developer_ids()
        if not dev_ids:
            raise ValueError("No developers to process")
        return len(dev_ids)

    async def generate_single_embedding(self, developer_id: int) -> None:
        """Generate embedding for a single developer.

        Raises:
            ValueError: If embedding is not configured.
        """
        from app.domains.open_source.services.open_source_embedding_service import (
            OpenSourceEmbeddingService,
        )
        from app.domains.shared.services.config_service import ConfigService
        from app.domains.shared.services.llm import LLMGateway

        config_service = ConfigService(self.session)
        llm_config = await config_service.get_llm_config()

        if not llm_config.embedding_enabled:
            raise ValueError("嵌入模型未启用")

        llm_gateway = LLMGateway(
            api_key=llm_config.api_key,
            api_base=llm_config.api_base,
            model=llm_config.model,
            embedding_model=llm_config.embedding_model,
            embedding_api_base=llm_config.embedding_api_base,
            embedding_api_key=llm_config.embedding_api_key,
            timeout=llm_config.timeout or 60,
            api_format=llm_config.api_format,
            embedding_api_format=llm_config.embedding_api_format,
        )

        embed_service = OpenSourceEmbeddingService(
            session=self.session,
            llm_gateway=llm_gateway,
            dimension=llm_config.embedding_dimension,
            model_name=llm_config.embedding_model,
        )

        await embed_service.get_or_create_embedding(developer_id)
        await self.session.commit()

    @staticmethod
    async def run_embedding_generation_background(
        developer_ids: list[int],
        batch_size: int,
        force: bool,
        progress_dict: dict,
    ) -> None:
        """Run embedding generation in background.

        Follows the same batch-loop pattern as the academic domain for:
        - Cancellation check between batches
        - Real-time progress updates
        - Per-batch exception isolation
        """
        from app.domains.open_source.services.open_source_embedding_service import (
            OpenSourceEmbeddingService,
        )
        from app.domains.shared.services.config_service import ConfigService
        from app.domains.shared.services.llm import LLMGateway

        try:
            async with AsyncSessionLocal() as session:
                config_service = ConfigService(session)
                llm_config = await config_service.get_llm_config()

                llm_gateway = LLMGateway(
                    api_key=llm_config.api_key,
                    api_base=llm_config.api_base,
                    model=llm_config.model,
                    embedding_model=llm_config.embedding_model,
                    embedding_api_base=llm_config.embedding_api_base,
                    embedding_api_key=llm_config.embedding_api_key,
                    timeout=llm_config.timeout or 60,
                    api_format=llm_config.api_format,
                    embedding_api_format=llm_config.embedding_api_format,
                )

                embed_service = OpenSourceEmbeddingService(
                    session=session,
                    llm_gateway=llm_gateway,
                    dimension=llm_config.embedding_dimension,
                    model_name=llm_config.embedding_model,
                    rate_limit_delay=1.0,
                )

                if llm_gateway.embedding_api_format == "minimax":
                    actual_batch_size = min(batch_size, 16)
                else:
                    actual_batch_size = min(batch_size, 64)

                processed = 0
                failed = 0

                for i in range(0, len(developer_ids), actual_batch_size):
                    if progress_dict["status"] == "cancelled":
                        logger.info("OS embedding generation cancelled")
                        return

                    batch = developer_ids[i : i + actual_batch_size]
                    batch_num = i // actual_batch_size + 1

                    try:
                        stats = await embed_service.batch_generate_embeddings(
                            developer_ids=batch,
                            batch_size=actual_batch_size,
                            force_regenerate=force,
                        )
                        processed += stats.get("processed", 0)
                        failed += stats.get("failed", 0)

                        # 实时更新进度
                        progress_dict["processed"] = processed
                        progress_dict["failed"] = failed
                        logger.info(
                            f"OS Progress: {processed}/{progress_dict['total']} processed, {failed} failed"
                        )

                    except Exception as e:
                        logger.error(f"OS batch {batch_num} failed: {e}")
                        failed += len(batch)
                        progress_dict["failed"] = failed

                progress_dict["status"] = "completed"
                progress_dict["completed_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

                logger.info(
                    f"OS embedding generation completed: processed={processed}, failed={failed}"
                )
        except Exception as e:
            logger.error(f"OS embedding generation failed: {e}")
            progress_dict["status"] = "error"
            progress_dict["error_message"] = str(e)
            progress_dict["completed_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    async def generate_embeddings(self, batch_size: int = 50) -> dict[str, Any]:
        """
        生成嵌入向量

        Args:
            batch_size: 批次大小

        Returns:
            dict: 操作结果
        """
        return await self.repo.generate_embeddings(batch_size=batch_size)
