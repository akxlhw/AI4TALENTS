"""
Fix Talent-School Relationships

This script fixes the talent-school relationship by:
1. Finding talents without school associations
2. Querying OpenAlex Authors API to get their last_known_institutions
3. Matching institutions to schools in the database
4. Updating talent records with school_id

Usage:
    python scripts/fix_talent_school_relation.py [--batch-size 500] [--dry-run]
"""
import time
import requests
import logging
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
from sqlalchemy import create_engine, select, or_
from sqlalchemy.orm import sessionmaker
from difflib import SequenceMatcher

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.talent import Talent
from app.models.school import School, SchoolAlias
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# OpenAlex API configuration
OPENALEX_BASE_URL = "https://api.openalex.org"
POLITE_POOL_EMAIL = "mailto:research@example.com"

# Processing configuration
BATCH_SIZE = 500  # Number of talents to process per batch
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 0.3  # Delay between API requests


class TalentSchoolFixer:
    """Fix talent-school relationships using OpenAlex data."""

    def __init__(self, db_url: str = None):
        self.db_url = db_url or settings.DATABASE_SYNC_URL
        self.engine = create_engine(self.db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)

        # Cache for school lookups
        self.school_name_cache: Dict[str, int] = {}
        self.school_openalex_cache: Dict[str, int] = {}

        self.stats = {
            'total_talents': 0,
            'talents_without_school': 0,
            'talents_processed': 0,
            'talents_updated': 0,
            'talents_matched': 0,
            'api_calls': 0,
            'api_errors': 0,
            'schools_created': 0,
        }

    def run(self, dry_run: bool = False, limit: int = None) -> Dict:
        """
        Run the fix process.

        Args:
            dry_run: If True, don't actually update the database
            limit: Maximum number of talents to process (for testing)

        Returns:
            Statistics dictionary
        """
        start_time = datetime.now()
        print("\n" + "=" * 70)
        print("[TalentSchoolFixer] Fixing Talent-School Relationships")
        print("=" * 70)
        print(f"Start time: {start_time}")
        print(f"Dry run: {dry_run}")
        print(f"Batch size: {BATCH_SIZE}")
        print()

        session = self.Session()

        try:
            # Step 1: Load school cache
            print("[Step 1] Loading school cache...")
            self._load_school_cache(session)
            print(f"  Loaded {len(self.school_name_cache)} schools by name")
            print(f"  Loaded {len(self.school_openalex_cache)} schools by OpenAlex ID")
            print()

            # Step 2: Find talents without school
            print("[Step 2] Finding talents without school association...")
            talents = self._find_talents_without_school(session, limit)
            self.stats['talents_without_school'] = len(talents)
            print(f"  Found {len(talents)} talents without school")
            print()

            if not talents:
                print("No talents to process. Done!")
                return self.stats

            # Step 3: Process in batches
            print("[Step 3] Processing talents in batches...")
            total = len(talents)
            processed = 0

            for i in range(0, total, BATCH_SIZE):
                batch = talents[i:i+BATCH_SIZE]
                batch_start = time.time()

                print(f"\n  Processing batch {i//BATCH_SIZE + 1} ({len(batch)} talents)...")

                updated_count = self._process_batch(session, batch, dry_run)

                self.stats['talents_processed'] += len(batch)
                self.stats['talents_updated'] += updated_count

                processed += len(batch)
                elapsed = time.time() - batch_start

                print(f"  Batch complete: {updated_count} updated, {elapsed:.1f}s")
                print(f"  Progress: {processed}/{total} ({processed/total*100:.1f}%)")

            # Summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            print("\n" + "=" * 70)
            print("[TalentSchoolFixer] Summary")
            print("=" * 70)
            print(f"Total talents: {self.stats['total_talents']}")
            print(f"Talents without school: {self.stats['talents_without_school']}")
            print(f"Talents processed: {self.stats['talents_processed']}")
            print(f"Talents updated: {self.stats['talents_updated']}")
            print(f"API calls: {self.stats['api_calls']}")
            print(f"API errors: {self.stats['api_errors']}")
            print(f"Schools created: {self.stats['schools_created']}")
            print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")

            if self.stats['talents_processed'] > 0:
                success_rate = self.stats['talents_updated'] / self.stats['talents_processed'] * 100
                print(f"Match rate: {success_rate:.1f}%")

            return self.stats

        finally:
            session.close()

    def _load_school_cache(self, session):
        """Load all schools into memory for fast lookup."""
        # Load by name
        schools = session.execute(select(School)).scalars().all()
        for school in schools:
            # Normalize name for matching
            normalized_name = self._normalize_name(school.school_name)
            self.school_name_cache[normalized_name] = school.school_id

            # Also cache by OpenAlex ID if available
            if school.source_record_id:
                self.school_openalex_cache[school.source_record_id] = school.school_id

        # Load aliases
        aliases = session.execute(select(SchoolAlias)).scalars().all()
        for alias in aliases:
            normalized_alias = self._normalize_name(alias.alias_name)
            self.school_name_cache[normalized_alias] = alias.school_id

    def _find_talents_without_school(self, session, limit: int = None) -> List[Talent]:
        """Find all talents without school association that have OpenAlex ID."""
        query = select(Talent).where(
            Talent.school_id.is_(None),
            Talent.source_record_id.isnot(None)
        )

        if limit:
            query = query.limit(limit)

        return session.execute(query).scalars().all()

    def _process_batch(self, session, talents: List[Talent], dry_run: bool) -> int:
        """Process a batch of talents."""
        updated = 0

        for talent in talents:
            try:
                # Get author details from OpenAlex
                author_data = self._get_author_details(talent.source_record_id)

                if not author_data:
                    continue

                institutions = author_data.get('last_known_institutions', [])

                if not institutions:
                    continue

                # Try to match institution to school
                school_id = self._match_institution_to_school(
                    session, institutions, dry_run
                )

                if school_id:
                    talent.school_id = school_id
                    updated += 1
                    self.stats['talents_matched'] += 1

                    if not dry_run:
                        session.commit()
                    else:
                        session.rollback()

            except Exception as e:
                logger.error(f"Error processing talent {talent.talent_id}: {e}")
                session.rollback()

        return updated

    def _get_author_details(self, openalex_id: str) -> Optional[Dict]:
        """Get author details from OpenAlex Authors API."""
        # Extract short ID if full URL
        short_id = openalex_id.split('/')[-1] if '/' in openalex_id else openalex_id

        url = f"{OPENALEX_BASE_URL}/authors/{short_id}"
        params = {'mailto': POLITE_POOL_EMAIL}

        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            self.stats['api_calls'] += 1

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"API returned {response.status_code} for {short_id}")
                self.stats['api_errors'] += 1

        except Exception as e:
            logger.warning(f"API error for {short_id}: {e}")
            self.stats['api_errors'] += 1

        return None

    def _match_institution_to_school(
        self, session, institutions: List[Dict], dry_run: bool
    ) -> Optional[int]:
        """
        Match an institution from OpenAlex to a school in the database.

        Tries multiple matching strategies:
        1. Exact OpenAlex ID match
        2. Exact name match
        3. Fuzzy name match
        """
        for inst in institutions:
            inst_name = inst.get('display_name', '')
            inst_id = inst.get('id', '')

            # Extract short ID
            short_id = inst_id.split('/')[-1] if inst_id else None

            # Strategy 1: Exact OpenAlex ID match
            if short_id and short_id in self.school_openalex_cache:
                return self.school_openalex_cache[short_id]

            # Strategy 2: Exact name match
            normalized_name = self._normalize_name(inst_name)
            if normalized_name in self.school_name_cache:
                return self.school_name_cache[normalized_name]

            # Strategy 3: Fuzzy name match
            school_id = self._fuzzy_match_school(inst_name)
            if school_id:
                return school_id

            # Strategy 4: Create new school if not found
            if inst_name and not dry_run:
                school_id = self._create_school(session, inst_name, short_id)
                if school_id:
                    return school_id

        return None

    def _normalize_name(self, name: str) -> str:
        """Normalize institution name for matching."""
        if not name:
            return ""
        return name.lower().strip().replace("-", " ").replace(",", "")

    def _fuzzy_match_school(self, name: str, threshold: float = 0.85) -> Optional[int]:
        """Fuzzy match institution name to school names."""
        normalized_name = self._normalize_name(name)

        best_match = None
        best_score = 0

        for school_name, school_id in self.school_name_cache.items():
            # Calculate similarity
            score = SequenceMatcher(None, normalized_name, school_name).ratio()

            if score > best_score and score >= threshold:
                best_score = score
                best_match = school_id

        return best_match

    def _create_school(self, session, name: str, openalex_id: str = None) -> Optional[int]:
        """Create a new school record."""
        from app.models.country import Country

        try:
            # Create school with minimal info
            # Country will be set to a default or determined from OpenAlex
            default_country = session.execute(
                select(Country).limit(1)
            ).scalar_one_or_none()

            if not default_country:
                logger.warning(f"Cannot create school {name}: no countries in database")
                return None

            school = School(
                school_name=name,
                country_id=default_country.country_id,
                is_visible=True,
                status="active",
                source_type="openalex",
                source_record_id=openalex_id,
            )

            session.add(school)
            session.flush()

            # Add to cache
            normalized_name = self._normalize_name(name)
            self.school_name_cache[normalized_name] = school.school_id
            if openalex_id:
                self.school_openalex_cache[openalex_id] = school.school_id

            self.stats['schools_created'] += 1
            logger.info(f"Created new school: {name}")

            return school.school_id

        except Exception as e:
            logger.error(f"Error creating school {name}: {e}")
            session.rollback()
            return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix talent-school relationships",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help="Number of talents to process per batch",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of talents to process (for testing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually update the database",
    )

    args = parser.parse_args()

    fixer = TalentSchoolFixer()
    result = fixer.run(dry_run=args.dry_run, limit=args.limit)

    print("\nDone!")


if __name__ == "__main__":
    main()
