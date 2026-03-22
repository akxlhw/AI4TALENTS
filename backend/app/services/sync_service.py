"""
Sync service for orchestrating data synchronization.
"""
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.openalex_client import OpenAlexClient, get_openalex_client
from app.repositories.sync_repository import SyncBatchRepository, RawSourceRecordRepository
from app.models.enums import SyncJobStatus, SourceType


logger = logging.getLogger(__name__)


@dataclass
class SyncProgress:
    """Progress information for sync operation."""
    batch_id: int
    batch_code: str
    status: str
    total_records: int
    processed_records: int
    failed_records: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    current_stage: str = ""
    error_message: Optional[str] = None


class SyncService:
    """
    Service for synchronizing data from OpenAlex.

    Handles the complete sync workflow:
    1. Create sync batch record
    2. Fetch institutions
    3. Fetch authors for selected institutions
    4. Store raw data
    5. Update batch status
    """

    def __init__(
        self,
        session: AsyncSession,
        client: Optional[OpenAlexClient] = None,
    ):
        self.session = session
        self.client = client or get_openalex_client()
        self.batch_repo = SyncBatchRepository(session)
        self.raw_repo = RawSourceRecordRepository(session)

    async def sync_institutions(
        self,
        country_codes: Optional[List[str]] = None,
        max_institutions: Optional[int] = None,
        batch_type: str = "full",
    ) -> SyncProgress:
        """
        Synchronize institutions from OpenAlex.

        Args:
            country_codes: List of country codes to sync (None for all)
            max_institutions: Maximum institutions to sync per country
            batch_type: 'full' or 'incremental'

        Returns:
            SyncProgress with sync results
        """
        logger.info(f"Starting institution sync for countries: {country_codes}")

        # Create batch
        config = {
            "country_codes": country_codes,
            "max_institutions": max_institutions,
        }
        batch = await self.batch_repo.create_batch(
            batch_type=batch_type,
            source_type=SourceType.OPENALEX.value,
            config_snapshot=config,
        )

        # Start batch
        await self.batch_repo.start_batch(batch.batch_id)
        await self.session.commit()

        total_records = 0
        success_records = 0
        failed_records = 0

        try:
            if country_codes:
                # Sync specific countries
                for country_code in country_codes:
                    count = await self._sync_institutions_by_country(
                        batch.batch_id,
                        country_code,
                        max_institutions,
                    )
                    total_records += count
                    success_records += count
            else:
                # Sync all institutions
                count = await self._sync_all_institutions(
                    batch.batch_id,
                    max_institutions,
                )
                total_records = count
                success_records = count

            # Complete batch
            await self.batch_repo.complete_batch(
                batch.batch_id,
                total_records=total_records,
                success_records=success_records,
                failed_records=failed_records,
            )
            await self.session.commit()

            logger.info(f"Institution sync completed: {success_records} records")

        except Exception as e:
            logger.error(f"Institution sync failed: {e}")
            await self.batch_repo.fail_batch(batch.batch_id, str(e))
            await self.session.commit()
            failed_records = total_records - success_records

        # Get updated batch
        batch = await self.batch_repo.get_batch(batch.batch_id)

        return SyncProgress(
            batch_id=batch.batch_id,
            batch_code=batch.batch_code,
            status=batch.status,
            total_records=batch.total_records,
            processed_records=batch.success_records,
            failed_records=batch.failed_records,
            started_at=batch.started_at,
            completed_at=batch.completed_at,
            error_message=batch.error_message,
        )

    async def _sync_institutions_by_country(
        self,
        batch_id: int,
        country_code: str,
        max_records: Optional[int] = None,
    ) -> int:
        """Sync institutions for a specific country."""
        logger.info(f"Syncing institutions for country: {country_code}")

        count = 0
        async for institution in self.client.iterate_institutions(
            country_code=country_code,
            institution_type="education",  # Focus on educational institutions
            max_records=max_records,
        ):
            await self.raw_repo.save_record(
                batch_id=batch_id,
                source_type="institution",
                source_id=self._extract_id(institution.get("id", "")),
                raw_data=institution,
            )
            count += 1

            # Commit in batches
            if count % 100 == 0:
                await self.session.commit()
                logger.info(f"  Saved {count} institutions for {country_code}")

        await self.session.commit()
        return count

    async def _sync_all_institutions(
        self,
        batch_id: int,
        max_records: Optional[int] = None,
    ) -> int:
        """Sync all institutions."""
        logger.info("Syncing all institutions")

        count = 0
        async for institution in self.client.iterate_institutions(
            institution_type="education",
            max_records=max_records,
        ):
            await self.raw_repo.save_record(
                batch_id=batch_id,
                source_type="institution",
                source_id=self._extract_id(institution.get("id", "")),
                raw_data=institution,
            )
            count += 1

            if count % 100 == 0:
                await self.session.commit()
                logger.info(f"  Saved {count} institutions")

        await self.session.commit()
        return count

    async def sync_institutions_by_ids(
        self,
        institution_ids: List[str],
    ) -> SyncProgress:
        """
        Synchronize specific institutions by their OpenAlex IDs.

        Args:
            institution_ids: List of OpenAlex institution IDs

        Returns:
            SyncProgress with sync results
        """
        logger.info(f"Syncing {len(institution_ids)} institutions by ID")

        config = {
            "institution_ids": institution_ids[:20],  # Store first 20 for reference
            "institution_count": len(institution_ids),
        }

        batch = await self.batch_repo.create_batch(
            batch_type="full",
            source_type=SourceType.OPENALEX.value,
            config_snapshot=config,
        )

        await self.batch_repo.start_batch(batch.batch_id)
        await self.session.commit()

        total_records = 0
        success_records = 0
        failed_records = 0

        try:
            for inst_id in institution_ids:
                try:
                    # Fetch institution by ID
                    institution = await self.client.get_institution_by_id(inst_id)
                    if institution:
                        await self.raw_repo.save_record(
                            batch_id=batch.batch_id,
                            source_type="institution",
                            source_id=inst_id,
                            raw_data=institution,
                        )
                        total_records += 1
                        success_records += 1
                except Exception as e:
                    logger.warning(f"Failed to fetch institution {inst_id}: {e}")
                    failed_records += 1

            await self.batch_repo.complete_batch(
                batch.batch_id,
                total_records=total_records,
                success_records=success_records,
                failed_records=failed_records,
            )
            await self.session.commit()

        except Exception as e:
            logger.error(f"Institution sync by ID failed: {e}")
            await self.batch_repo.fail_batch(batch.batch_id, str(e))
            await self.session.commit()

        batch = await self.batch_repo.get_batch(batch.batch_id)

        return SyncProgress(
            batch_id=batch.batch_id,
            batch_code=batch.batch_code,
            status=batch.status,
            total_records=batch.total_records,
            processed_records=batch.success_records,
            failed_records=batch.failed_records,
            started_at=batch.started_at,
            completed_at=batch.completed_at,
            error_message=batch.error_message,
        )

    async def sync_authors_for_institutions(
        self,
        institution_ids: List[str],
        max_authors_per_institution: Optional[int] = None,
    ) -> SyncProgress:
        """
        Synchronize authors for specified institutions.

        Args:
            institution_ids: List of OpenAlex institution IDs
            max_authors_per_institution: Maximum authors per institution

        Returns:
            SyncProgress with sync results
        """
        logger.info(f"Starting author sync for {len(institution_ids)} institutions")

        config = {
            "institution_ids": institution_ids[:10],  # Store first 10 for reference
            "institution_count": len(institution_ids),
            "max_authors_per_institution": max_authors_per_institution,
        }

        batch = await self.batch_repo.create_batch(
            batch_type="full",
            source_type=SourceType.OPENALEX.value,
            config_snapshot=config,
        )

        await self.batch_repo.start_batch(batch.batch_id)
        await self.session.commit()

        total_records = 0
        success_records = 0
        failed_records = 0

        try:
            for inst_id in institution_ids:
                try:
                    count = await self._sync_authors_for_institution(
                        batch.batch_id,
                        inst_id,
                        max_authors_per_institution,
                    )
                    total_records += count
                    success_records += count
                except Exception as e:
                    logger.error(f"Failed to sync authors for {inst_id}: {e}")
                    failed_records += 1

            await self.batch_repo.complete_batch(
                batch.batch_id,
                total_records=total_records,
                success_records=success_records,
                failed_records=failed_records,
            )
            await self.session.commit()

        except Exception as e:
            logger.error(f"Author sync failed: {e}")
            await self.batch_repo.fail_batch(batch.batch_id, str(e))
            await self.session.commit()

        batch = await self.batch_repo.get_batch(batch.batch_id)

        return SyncProgress(
            batch_id=batch.batch_id,
            batch_code=batch.batch_code,
            status=batch.status,
            total_records=batch.total_records,
            processed_records=batch.success_records,
            failed_records=batch.failed_records,
            started_at=batch.started_at,
            completed_at=batch.completed_at,
            current_stage="authors",
            error_message=batch.error_message,
        )

    async def _sync_authors_for_institution(
        self,
        batch_id: int,
        institution_id: str,
        max_records: Optional[int] = None,
    ) -> int:
        """Sync authors for a specific institution."""
        logger.info(f"Syncing authors for institution: {institution_id}")

        count = 0
        async for author in self.client.iterate_authors(
            institution_id=institution_id,
            max_records=max_records,
        ):
            await self.raw_repo.save_record(
                batch_id=batch_id,
                source_type="author",
                source_id=self._extract_id(author.get("id", "")),
                raw_data=author,
            )
            count += 1

            if count % 50 == 0:
                await self.session.commit()
                logger.info(f"    Saved {count} authors")

        await self.session.commit()
        return count

    async def get_sync_progress(self, batch_id: int) -> Optional[SyncProgress]:
        """Get progress for a sync batch."""
        batch = await self.batch_repo.get_batch(batch_id)
        if not batch:
            return None

        return SyncProgress(
            batch_id=batch.batch_id,
            batch_code=batch.batch_code,
            status=batch.status,
            total_records=batch.total_records,
            processed_records=batch.success_records,
            failed_records=batch.failed_records,
            started_at=batch.started_at,
            completed_at=batch.completed_at,
        )

    @staticmethod
    def _extract_id(url_or_id: str) -> str:
        """Extract ID from OpenAlex URL or return as-is."""
        if url_or_id.startswith("https://"):
            return url_or_id.rstrip("/").split("/")[-1]
        return url_or_id
