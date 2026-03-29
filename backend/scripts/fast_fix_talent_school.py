"""
Fast Fix Talent-School Relationships

This script fixes talent-school relationships by:
1. Getting talents without school associations
2. Querying OpenAlex Works API (not Authors API) to get institution info
3. Matching institutions to schools in database

This is MUCH FASTER than using Authors API because:
- We can batch query works by author IDs
- Works API includes institution info in authorships[].institutions

Usage:
    python scripts/fast_fix_talent_school.py [--batch-size 100]
"""
import time
import requests
import logging
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.talent import Talent
from app.models.school import School
from app.models.country import Country
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
BATCH_SIZE = 100  # Number of authors to query per API call
REQUEST_TIMEOUT = 60
REQUEST_DELAY = 0.5


class FastTalentSchoolFixer:
    """Fix talent-school relationships using Works API (faster)."""

    def __init__(self, db_url: str = None):
        self.db_url = db_url or settings.DATABASE_SYNC_URL
        self.engine = create_engine(self.db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)

        # Cache for school lookups
        self.school_cache: Dict[str, int] = {}

        self.stats = {
            'talents_processed': 0,
            'talents_updated': 0,
            'api_calls': 0,
            'schools_created': 0,
        }

    def run(self, limit: int = None) -> Dict:
        """Run the fix process."""
        start_time = datetime.now()
        print("\n" + "=" * 70)
        print("[FastFix] Fixing Talent-School Relationships (Using Works API)")
        print("=" * 70)
        print(f"Start time: {start_time}")
        print(f"Batch size: {BATCH_SIZE}")
        print()

        session = self.Session()

        try:
            # Step 1: Load school cache
            print("[Step 1] Loading school cache...")
            self._load_school_cache(session)
            print(f"  Loaded {len(self.school_cache)} schools")
            print()

            # Step 2: Find talents without school
            print("[Step 2] Finding talents without school association...")
            query = select(Talent).where(
                Talent.school_id.is_(None),
                Talent.source_record_id.isnot(None)
            )
            if limit:
                query = query.limit(limit)

            talents = session.execute(query).scalars().all()
            print(f"  Found {len(talents)} talents to process")
            print()

            if not talents:
                print("No talents to process. Done!")
                return self.stats

            # Step 3: Process in batches using Works API
            print("[Step 3] Processing talents in batches...")
            total = len(talents)
            processed = 0
            updated = 0

            # Build author ID list
            author_ids = [t.source_record_id for t in talents]
            author_to_talent = {t.source_record_id: t for t in talents}

            for i in range(0, len(author_ids), BATCH_SIZE):
                batch_ids = author_ids[i:i+BATCH_SIZE]
                batch_start = time.time()

                # Query Works API with author filter
                institutions_map = self._get_institutions_from_works(batch_ids)

                # Update talents
                for author_id, inst_info in institutions_map.items():
                    if inst_info and inst_info.get('display_name'):
                        talent = author_to_talent.get(author_id)
                        if talent:
                            school_id = self._find_or_create_school(
                                session,
                                inst_info.get('display_name'),
                                inst_info.get('id')
                            )
                            if school_id:
                                talent.school_id = school_id
                                updated += 1
                                self.stats['talents_updated'] += 1

                session.commit()
                processed += len(batch_ids)
                self.stats['talents_processed'] = processed

                elapsed = time.time() - batch_start
                print(f"  Batch {i//BATCH_SIZE + 1}: {len(batch_ids)} authors, {len(institutions_map)} with institutions, {updated} updated, {elapsed:.1f}s")
                print(f"  Progress: {processed}/{total} ({processed/total*100:.1f}%)")

                time.sleep(REQUEST_DELAY)

            # Summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            print("\n" + "=" * 70)
            print("[FastFix] Summary")
            print("=" * 70)
            print(f"Talents processed: {self.stats['talents_processed']}")
            print(f"Talents updated: {self.stats['talents_updated']}")
            print(f"API calls: {self.stats['api_calls']}")
            print(f"Schools created: {self.stats['schools_created']}")
            print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
            print(f"Match rate: {self.stats['talents_updated']/self.stats['talents_processed']*100:.1f}%" if self.stats['talents_processed'] > 0 else "N/A")

            return self.stats

        finally:
            session.close()

    def _load_school_cache(self, session):
        """Load all schools into memory for fast lookup."""
        schools = session.execute(select(School)).scalars().all()
        for school in schools:
            # Cache by name
            normalized_name = self._normalize_name(school.school_name)
            self.school_cache[normalized_name] = school.school_id

            # Cache by OpenAlex ID
            if school.source_record_id:
                self.school_cache[school.source_record_id] = school.school_id

    def _get_institutions_from_works(self, author_ids: List[str]) -> Dict[str, Dict]:
        """
        Get institution info from Works API by filtering on author IDs.

        This is more efficient than Authors API because we can batch query.
        """
        result = {}

        # Build filter: author.id:A123|A456|A789
        author_filter = "|".join([aid.split('/')[-1] if '/' in aid else aid for aid in author_ids])

        works_url = f"{OPENALEX_BASE_URL}/works"
        params = {
            'filter': f'author.id:{author_filter}',
            'per-page': 100,  # Max per page
            'mailto': POLITE_POOL_EMAIL,
        }

        try:
            response = requests.get(works_url, params=params, timeout=REQUEST_TIMEOUT)
            self.stats['api_calls'] += 1

            if response.status_code == 200:
                data = response.json()
                works = data.get('results', [])

                for work in works:
                    for authorship in work.get('authorships', []):
                        author = authorship.get('author', {})
                        author_id = author.get('id', '')

                        if author_id and author_id not in result:
                            institutions = authorship.get('institutions', [])
                            if institutions:
                                inst = institutions[0]
                                result[author_id] = {
                                    'id': inst.get('id', '').split('/')[-1] if inst.get('id') else None,
                                    'display_name': inst.get('display_name'),
                                }

            else:
                logger.warning(f"API returned {response.status_code}")

        except Exception as e:
            logger.error(f"API error: {e}")

        return result

    def _normalize_name(self, name: str) -> str:
        """Normalize institution name for matching."""
        if not name:
            return ""
        return name.lower().strip().replace("-", " ").replace(",", "")

    def _find_or_create_school(self, session, name: str, openalex_id: str = None) -> Optional[int]:
        """Find or create a school."""
        if not name:
            return None

        # Check cache by OpenAlex ID
        if openalex_id and openalex_id in self.school_cache:
            return self.school_cache[openalex_id]

        # Check cache by name
        normalized_name = self._normalize_name(name)
        if normalized_name in self.school_cache:
            return self.school_cache[normalized_name]

        # Check database
        existing = session.execute(
            select(School).where(School.school_name == name)
        ).scalar_one_or_none()

        if existing:
            self.school_cache[normalized_name] = existing.school_id
            if openalex_id:
                self.school_cache[openalex_id] = existing.school_id
            return existing.school_id

        # Create new school
        try:
            default_country = session.execute(
                select(Country).limit(1)
            ).scalar_one_or_none()

            if not default_country:
                return None

            school = School(
                school_name=name,
                country_id=default_country.country_id,
                is_visible=True,
                status='active',
                source_type='openalex',
                source_record_id=openalex_id,
            )
            session.add(school)
            session.flush()

            self.school_cache[normalized_name] = school.school_id
            if openalex_id:
                self.school_cache[openalex_id] = school.school_id

            self.stats['schools_created'] += 1
            return school.school_id

        except Exception as e:
            logger.error(f"Error creating school: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(
        description="Fast fix talent-school relationships",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help="Number of authors to query per API call",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of talents to process",
    )

    args = parser.parse_args()

    fixer = FastTalentSchoolFixer()
    result = fixer.run(limit=args.limit)

    print("\nDone!")


if __name__ == "__main__":
    main()
