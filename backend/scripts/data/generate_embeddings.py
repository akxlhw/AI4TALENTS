"""
Batch embedding generation script.
批量嵌入向量生成脚本 - v1.4

Features:
- Batch processing with configurable size
- Checkpoint/resume support
- Rate limiting
- Progress tracking
- Dry run mode

Usage:
    python scripts/generate_embeddings.py --help
    python scripts/generate_embeddings.py --dry-run
    python scripts/generate_embeddings.py --batch-size 50 --rate-limit 1.0
    python scripts/generate_embeddings.py --resume
    python scripts/generate_embeddings.py --reset
"""

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.config import settings
from app.domains.academic.models.talent import Talent
from app.domains.shared.services.llm import create_llm_gateway
from app.domains.academic.services.embedding.embedding_service import EmbeddingService
from app.domains.shared.services.cache.cache_manager import CacheManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Checkpoint:
    """进度检查点"""
    last_talent_id: int
    processed_count: int
    failed_ids: List[int]
    timestamp: str
    model_name: str


class EmbeddingGenerator:
    """嵌入向量生成�?
    支持断点续传的批量嵌入生成�?    """

    CHECKPOINT_DIR = Path(__file__).parent.parent.parent / "data"
    CHECKPOINT_FILE = CHECKPOINT_DIR / "embedding_checkpoint.json"

    def __init__(
        self,
        batch_size: int = 100,
        rate_limit_delay: float = 1.0,
        model_name: str | None = None,
    ):
        """
        初始化生成器

        Args:
            batch_size: 批次大小
            rate_limit_delay: 限流延迟（秒�?            model_name: 模型名称
        """
        self.batch_size = batch_size
        self.rate_limit_delay = rate_limit_delay
        self.model_name = model_name or settings.LLM_EMBEDDING_MODEL
        self.checkpoint: Optional[Checkpoint] = None

        # Ensure checkpoint directory exists
        self.CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    def load_checkpoint(self) -> Optional[Checkpoint]:
        """加载检查点"""
        if not self.CHECKPOINT_FILE.exists():
            return None

        try:
            data = json.loads(self.CHECKPOINT_FILE.read_text())
            checkpoint = Checkpoint(**data)
            logger.info(f"Loaded checkpoint: last_talent_id={checkpoint.last_talent_id}, "
                       f"processed={checkpoint.processed_count}")
            return checkpoint
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def save_checkpoint(self, checkpoint: Checkpoint):
        """保存检查点"""
        try:
            self.CHECKPOINT_FILE.write_text(json.dumps(asdict(checkpoint), indent=2))
            logger.debug(f"Saved checkpoint: last_talent_id={checkpoint.last_talent_id}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def reset_checkpoint(self):
        """重置检查点"""
        if self.CHECKPOINT_FILE.exists():
            self.CHECKPOINT_FILE.unlink()
            logger.info("Checkpoint reset")

    async def get_talent_ids(self, session, resume: bool = True) -> List[int]:
        """
        获取待处理的人才 ID 列表

        Args:
            session: 数据库会�?            resume: 是否从检查点恢复

        Returns:
            List[int]: 人才 ID 列表
        """
        query = select(Talent.talent_id).where(
            Talent.is_visible.is_(True)
        ).order_by(Talent.talent_id)

        if resume and self.checkpoint:
            query = query.where(Talent.talent_id > self.checkpoint.last_talent_id)

        result = await session.execute(query)
        return [row[0] for row in result.fetchall()]

    async def progress_callback(self, processed: int, total: int, batch_num: int):
        """进度回调"""
        progress = (processed / total * 100) if total > 0 else 0
        logger.info(f"Batch {batch_num}: {processed}/{total} ({progress:.1f}%)")

    async def run(
        self,
        dry_run: bool = False,
        resume: bool = True,
        force: bool = False,
    ) -> dict:
        """
        执行批量嵌入生成

        Args:
            dry_run: 仅统计不执行
            resume: 是否从检查点恢复
            force: 是否强制重新生成

        Returns:
            dict: 执行结果
        """
        # 检�?LLM 是否启用
        if not settings.LLM_ENABLED:
            logger.error("LLM is not enabled. Set LLM_ENABLED=true in .env")
            return {"error": "LLM not enabled"}

        # 加载检查点
        if resume:
            self.checkpoint = self.load_checkpoint()
        else:
            self.checkpoint = None

        # 创建 LLM 网关
        llm_gateway = create_llm_gateway()
        if not llm_gateway:
            logger.error("Failed to create LLM gateway. Check LLM_API_KEY")
            return {"error": "Failed to create LLM gateway"}

        async with async_session_maker() as session:
            # 获取人才 ID
            talent_ids = await self.get_talent_ids(session, resume)
            total = len(talent_ids)

            if total == 0:
                logger.info("No talents to process")
                return {"total": 0, "processed": 0}

            logger.info(f"Found {total} talents to process")

            if dry_run:
                estimated_batches = (total + self.batch_size - 1) // self.batch_size
                logger.info(f"Dry run: would process {total} talents in {estimated_batches} batches")
                return {
                    "total": total,
                    "estimated_batches": estimated_batches,
                    "batch_size": self.batch_size,
                }

            # 创建嵌入服务
            embed_service = EmbeddingService(
                session=session,
                llm_gateway=llm_gateway,
                model_name=self.model_name,
                rate_limit_delay=self.rate_limit_delay,
            )

            # 执行批量生成
            start_time = datetime.utcnow()
            stats = await embed_service.batch_generate_embeddings(
                talent_ids=talent_ids,
                batch_size=self.batch_size,
                force_regenerate=force,
                progress_callback=self.progress_callback,
            )
            elapsed = (datetime.utcnow() - start_time).total_seconds()

            # 打印结果
            logger.info("=" * 50)
            logger.info("Embedding Generation Complete")
            logger.info("=" * 50)
            logger.info(f"Total:     {stats['total']}")
            logger.info(f"Processed: {stats['processed']}")
            logger.info(f"Skipped:   {stats['skipped']}")
            logger.info(f"Failed:    {stats['failed']}")
            logger.info(f"Time:      {elapsed:.1f}s")

            if stats['failed_ids']:
                logger.warning(f"Failed IDs: {stats['failed_ids'][:10]}...")

            return stats


async def main():
    """主函�?""
    parser = argparse.ArgumentParser(
        description="Batch generate embeddings for talents"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only count talents, don't generate embeddings"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=settings.EMBEDDING_BATCH_SIZE,
        help=f"Batch size (default: {settings.EMBEDDING_BATCH_SIZE})"
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="Rate limit delay between batches in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Don't resume from checkpoint, start from beginning"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset checkpoint before starting"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regenerate even if embedding exists"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Embedding model name (default: from settings)"
    )

    args = parser.parse_args()

    # 创建生成�?    generator = EmbeddingGenerator(
        batch_size=args.batch_size,
        rate_limit_delay=args.rate_limit,
        model_name=args.model,
    )

    # 重置检查点
    if args.reset:
        generator.reset_checkpoint()

    # 执行
    result = await generator.run(
        dry_run=args.dry_run,
        resume=not args.no_resume,
        force=args.force,
    )

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    print(json.dumps(result, indent=2, default=str))
