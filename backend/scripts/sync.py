"""
OpenAlex data synchronization script.
Fetches data from OpenAlex API and stores it in the database.

Usage:
    python scripts/sync.py [options]

Options:
    --type {full,incremental}  Sync type (default: full)
    --countries CODES          Comma-separated country codes (e.g., US,CN,GB)
    --max-institutions N       Maximum institutions to sync per country
    --max-authors N            Maximum authors per institution
    --dry-run                  Test run without saving to database
"""
import asyncio
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.sync_service import SyncService
from app.services.openalex_client import OpenAlexClient
from app.repositories.sync_repository import SyncBatchRepository


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_institution_sync(
    countries: Optional[List[str]] = None,
    max_institutions: Optional[int] = None,
    batch_type: str = "full",
) -> dict:
    """
    Run institution synchronization.

    Args:
        countries: List of country codes to sync
        max_institutions: Maximum institutions per country
        batch_type: 'full' or 'incremental'

    Returns:
        Sync results
    """
    async with AsyncSessionLocal() as session:
        service = SyncService(session)
        progress = await service.sync_institutions(
            country_codes=countries,
            max_institutions=max_institutions,
            batch_type=batch_type,
        )

        return {
            "batch_id": progress.batch_id,
            "batch_code": progress.batch_code,
            "status": progress.status,
            "total_records": progress.total_records,
            "success_records": progress.processed_records,
            "failed_records": progress.failed_records,
            "started_at": progress.started_at.isoformat() if progress.started_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
            "error_message": progress.error_message,
        }


async def run_author_sync(
    institution_ids: List[str],
    max_authors: Optional[int] = None,
) -> dict:
    """
    Run author synchronization for specified institutions.

    Args:
        institution_ids: List of OpenAlex institution IDs
        max_authors: Maximum authors per institution

    Returns:
        Sync results
    """
    async with AsyncSessionLocal() as session:
        service = SyncService(session)
        progress = await service.sync_authors_for_institutions(
            institution_ids=institution_ids,
            max_authors_per_institution=max_authors,
        )

        return {
            "batch_id": progress.batch_id,
            "batch_code": progress.batch_code,
            "status": progress.status,
            "total_records": progress.total_records,
            "success_records": progress.processed_records,
            "failed_records": progress.failed_records,
            "started_at": progress.started_at.isoformat() if progress.started_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
        }


async def test_openalex_connection() -> bool:
    """Test connection to OpenAlex API."""
    print("\nTesting OpenAlex API connection...")

    try:
        client = OpenAlexClient(
            email=settings.OPENALEX_EMAIL,
            rate_limit=settings.OPENALEX_RATE_LIMIT,
        )

        # Try fetching a single institution
        result = await client.get_institutions(
            country_code="US",
            institution_type="education",
            per_page=1,
        )

        count = result.get("meta", {}).get("count", 0)
        print(f"  [OK] Connection successful")
        print(f"  [OK] Found {count} US educational institutions")

        return True

    except Exception as e:
        print(f"  [FAIL] Connection failed: {e}")
        return False


async def run_sync(
    sync_type: str = "full",
    countries: Optional[List[str]] = None,
    max_institutions: Optional[int] = None,
    max_authors: Optional[int] = None,
    dry_run: bool = False,
):
    """
    Run the complete sync workflow.

    Args:
        sync_type: 'full' or 'incremental'
        countries: Country codes to sync
        max_institutions: Max institutions per country
        max_authors: Max authors per institution
        dry_run: Test mode without database operations
    """
    start_time = datetime.now()
    print("\n" + "="*60)
    print("智能人才库 - OpenAlex 数据同步")
    print("="*60)
    print(f"开始时间: {start_time}")
    print(f"同步类型: {sync_type}")
    print(f"目标国家: {countries or '全部'}")
    print(f"API配置: {settings.OPENALEX_BASE_URL}")
    print(f"速率限制: {settings.OPENALEX_RATE_LIMIT} 请求/秒")
    if dry_run:
        print("*** DRY RUN 模式 - 不写入数据库 ***")

    # Test connection
    if not await test_openalex_connection():
        print("\n同步失败: 无法连接到 OpenAlex API")
        return

    if dry_run:
        print("\nDry run 完成，未执行实际同步")
        return

    # Step 1: Sync institutions
    print("\n" + "-"*60)
    print("步骤 1: 同步机构数据")
    print("-"*60)

    inst_result = await run_institution_sync(
        countries=countries,
        max_institutions=max_institutions,
        batch_type=sync_type,
    )

    print(f"\n机构同步结果:")
    print(f"  批次ID: {inst_result['batch_id']}")
    print(f"  批次号: {inst_result['batch_code']}")
    print(f"  状态: {inst_result['status']}")
    print(f"  总记录数: {inst_result['total_records']}")
    print(f"  成功: {inst_result['success_records']}")
    print(f"  失败: {inst_result['failed_records']}")

    if inst_result['error_message']:
        print(f"  错误: {inst_result['error_message']}")

    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n" + "="*60)
    print("同步完成")
    print("="*60)
    print(f"结束时间: {end_time}")
    print(f"耗时: {duration:.2f} 秒")
    print(f"机构记录: {inst_result['success_records']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OpenAlex 数据同步脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--type",
        choices=["full", "incremental"],
        default="full",
        help="同步类型 (默认: full)",
    )

    parser.add_argument(
        "--countries",
        type=str,
        help="目标国家代码，逗号分隔 (例如: US,CN,GB)",
    )

    parser.add_argument(
        "--max-institutions",
        type=int,
        help="每个国家最大机构数",
    )

    parser.add_argument(
        "--max-authors",
        type=int,
        help="每个机构最大作者数",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="测试模式，不写入数据库",
    )

    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="仅测试API连接",
    )

    args = parser.parse_args()

    # Parse countries
    countries = None
    if args.countries:
        countries = [c.strip().upper() for c in args.countries.split(",")]

    # Run
    if args.test_connection:
        asyncio.run(test_openalex_connection())
    else:
        asyncio.run(run_sync(
            sync_type=args.type,
            countries=countries,
            max_institutions=args.max_institutions,
            max_authors=args.max_authors,
            dry_run=args.dry_run,
        ))


if __name__ == "__main__":
    main()
