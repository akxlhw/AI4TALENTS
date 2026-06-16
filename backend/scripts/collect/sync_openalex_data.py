"""
OpenAlex data sync script - Fetches real data from OpenAlex API.
Includes professors, students, and graduates.
"""
import asyncio
import random
from datetime import datetime

import httpx
from sqlalchemy import create_engine, text

# OpenAlex API configuration
OPENALEX_BASE_URL = "https://api.openalex.org"

# Target institutions with CORRECT OpenAlex IDs (verified)
TARGET_INSTITUTIONS = [
    {"name": "Harvard University", "openalex_id": "I136199984", "country": "US"},
    {"name": "Stanford University", "openalex_id": "I97018004", "country": "US"},
    {"name": "Massachusetts Institute of Technology", "openalex_id": "I63966007", "country": "US"},
    {"name": "University of California, Berkeley", "openalex_id": "I95457486", "country": "US"},
    {"name": "University of Cambridge", "openalex_id": "I241749", "country": "GB"},
    {"name": "University of Oxford", "openalex_id": "I40120149", "country": "GB"},
    {"name": "ETH Zurich", "openalex_id": "I35440088", "country": "CH"},
    {"name": "National University of Singapore", "openalex_id": "I165932596", "country": "SG"},
    {"name": "Imperial College London", "openalex_id": "I47508984", "country": "GB"},
    {"name": "Tsinghua University", "openalex_id": "I99065089", "country": "CN"},
    {"name": "Peking University", "openalex_id": "I20231570", "country": "CN"},
    {"name": "University of Tokyo", "openalex_id": "I74801974", "country": "JP"},
]


class OpenAlexSync:
    """Sync real data from OpenAlex API."""

    def __init__(self, db_path: str = "./talent.db"):
        self.engine = create_engine(f'sqlite:///{db_path}')
        self.client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        await self.client.aclose()

    async def fetch_author_works(self, author_openalex_id: str, max_works: int = 10) -> list[dict]:
        """Fetch top works for an author, sorted by citation count."""
        url = f"{OPENALEX_BASE_URL}/works"

        # Filter by author and sort by cited_by_count descending
        params = {
            "filter": f"author.id:{author_openalex_id}",
            "sort": "cited_by_count:desc",
            "per-page": max_works,
        }

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            print(f"      Error fetching works: {e}")
            return []

    async def fetch_authors_by_institution(
        self,
        institution_id: str,
        max_authors: int = 100,
        min_works: int = None
    ) -> list[dict]:
        """Fetch authors from a specific institution with optional filters."""
        authors = []
        page = 1
        per_page = 100

        url = f"{OPENALEX_BASE_URL}/authors"

        while len(authors) < max_authors:
            # Build filter
            filters = [f"last_known_institutions.id:{institution_id}"]
            if min_works is not None:
                filters.append(f"works_count:>{min_works}")

            params = {
                "filter": ",".join(filters),
                "per-page": per_page,
                "page": page,
            }

            try:
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                if not results:
                    break

                authors.extend(results)
                print(f"    Fetched {len(authors)} authors...")

                # Check if there are more pages
                total_count = data.get("meta", {}).get("count", 0)
                if len(authors) >= total_count or len(results) < per_page:
                    break

                page += 1

            except httpx.HTTPStatusError as e:
                print(f"    HTTP error: {e.response.status_code}")
                break
            except Exception as e:
                print(f"    Error: {e}")
                break

        return authors[:max_authors]

    async def fetch_authors_random(
        self,
        institution_id: str,
        max_authors: int = 50,
        works_range: tuple = (1, 20)
    ) -> list[dict]:
        """Fetch authors within a specific works count range (for students)."""
        authors = []
        page = 1
        per_page = 100

        url = f"{OPENALEX_BASE_URL}/authors"

        # Use works_count range filter
        filters = [
            f"last_known_institutions.id:{institution_id}",
            f"works_count:{works_range[0]}-{works_range[1]}"
        ]

        params = {
            "filter": ",".join(filters),
            "per-page": per_page,
            "page": page,
        }

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if results:
                # Random sample if more results than needed
                if len(results) > max_authors:
                    results = random.sample(results, max_authors)
                authors = results
                print(f"    Fetched {len(authors)} potential students...")

        except httpx.HTTPStatusError as e:
            print(f"    HTTP error: {e.response.status_code}")
        except Exception as e:
            print(f"    Error: {e}")

        return authors

    def determine_role_type(self, author: dict) -> tuple:
        """
        Determine if author is professor, student, or graduated.
        Returns (role_type, confidence, reason)
        """
        works_count = author.get("works_count", 0)
        cited_by_count = author.get("cited_by_count", 0)
        summary_stats = author.get("summary_stats", {})
        h_index = summary_stats.get("h_index", 0) if summary_stats else 0

        # Decision logic - adjusted for better student detection
        if works_count >= 50 and h_index >= 20:
            return "professor", 0.95, "High publication count and H-index"
        elif works_count >= 30 and cited_by_count >= 1000:
            return "professor", 0.90, "High publication and citation count"
        elif works_count >= 20 and h_index >= 10:
            return "professor", 0.85, "Mid-career researcher"
        elif works_count <= 8:
            # Low publication count = likely student
            return "student", 0.80, "Low publication count, likely student"
        elif works_count <= 15 and cited_by_count < 200:
            # Very low citations with few works = student
            return "student", 0.75, "Early career student"
        elif 8 < works_count < 20:
            return "graduated", 0.70, "Mid-level output, likely graduated"
        else:
            return "professor", 0.60, "Default to professor"

    def extract_topics(self, author: dict) -> list[str]:
        """Extract research topics from author data."""
        x_concepts = author.get("x_concepts", [])
        topics = []

        for concept in x_concepts[:5]:
            if concept.get("score", 0) > 0.3:
                name = concept.get("display_name", "")
                if name:
                    topics.append(name)

        return topics

    def clean_database(self):
        """Clean existing test data."""
        with self.engine.connect() as conn:
            print("Cleaning existing data...")

            conn.execute(text("DELETE FROM core_collaboration"))
            conn.execute(text("DELETE FROM core_talent"))
            conn.execute(text("DELETE FROM core_school"))
            conn.execute(text("DELETE FROM iam_favorite_talent"))

            conn.commit()
            print("  Database cleaned.")

    def insert_schools(self) -> dict[str, int]:
        """Insert target institutions."""
        school_ids = {}

        with self.engine.connect() as conn:
            print("\nInserting institutions...")

            for i, inst in enumerate(TARGET_INSTITUTIONS, start=1):
                conn.execute(text('''
                    INSERT INTO core_school (school_id, school_name, country_id, is_visible, status, created_at, updated_at)
                    VALUES (:id, :name, 1, 1, 'active', :now, :now)
                '''), {
                    "id": i,
                    "name": inst["name"],
                    "now": datetime.now()
                })
                school_ids[inst["openalex_id"]] = i
                print(f"  + {inst['name']}")

            conn.commit()

        return school_ids

    async def sync_authors(self, school_ids: dict[str, int], professors_per_school: int = 50, students_per_school: int = 30):
        """Sync authors from all institutions."""
        print(f"\nSyncing authors ({professors_per_school} professors, {students_per_school} students per school)...")

        total_authors = 0
        role_counts = {"professor": 0, "student": 0, "graduated": 0, "unknown": 0}

        for inst in TARGET_INSTITUTIONS:
            openalex_id = inst["openalex_id"]
            school_id = school_ids.get(openalex_id)

            if not school_id:
                continue

            print(f"\n  {inst['name']}:")

            # 1. Fetch professors (high works count)
            print("    Fetching professors...")
            prof_authors = await self.fetch_authors_by_institution(
                openalex_id,
                max_authors=professors_per_school,
                min_works=30  # At least 30 works for professors
            )

            # 2. Fetch students (low works count)
            print("    Fetching students...")
            student_authors = await self.fetch_authors_random(
                openalex_id,
                max_authors=students_per_school,
                works_range=(1, 15)  # 1-15 works = likely students
            )

            # Combine all authors
            all_authors = prof_authors + student_authors
            print(f"    Total: {len(all_authors)} authors")

            with self.engine.connect() as conn:
                for author in all_authors:
                    if not author:
                        continue

                    role_type, confidence, reason = self.determine_role_type(author)
                    role_counts[role_type] = role_counts.get(role_type, 0) + 1

                    topics = self.extract_topics(author)
                    name = author.get("display_name", "")

                    if not name:
                        continue

                    summary_stats = author.get("summary_stats", {})
                    h_index = summary_stats.get("h_index", 0) if summary_stats else 0

                    try:
                        conn.execute(text('''
                            INSERT INTO core_talent (
                                name, name_en, orcid, role_type, role_confidence,
                                school_id, current_title, works_count, cited_by_count,
                                h_index, latest_active_year, topic_tags, department_name,
                                visibility_status, is_visible, source_type, source_record_id,
                                created_at, updated_at
                            ) VALUES (
                                :name, :name_en, :orcid, :role_type, :role_confidence,
                                :school_id, :current_title, :works_count, :cited_by_count,
                                :h_index, :latest_active_year, :topic_tags, :department_name,
                                'active', 1, 'openalex', :source_id,
                                :now, :now
                            )
                        '''), {
                            "name": name,
                            "name_en": name,
                            "orcid": author.get("orcid"),
                            "role_type": role_type,
                            "role_confidence": confidence,
                            "school_id": school_id,
                            "current_title": None,
                            "works_count": author.get("works_count", 0),
                            "cited_by_count": author.get("cited_by_count", 0),
                            "h_index": h_index,
                            "latest_active_year": 2024 if author.get("works_count", 0) > 0 else None,
                            "topic_tags": str(topics),
                            "department_name": None,
                            "source_id": author.get("id", ""),
                            "now": datetime.now()
                        })

                        # Get the inserted talent_id
                        result = conn.execute(text("SELECT last_insert_rowid()"))
                        talent_id = result.scalar()
                        total_authors += 1

                        # Fetch and insert representative works (only for professors with works > 5)
                        if role_type == "professor" and author.get("works_count", 0) > 5:
                            author_openalex_id = author.get("id", "").replace("https://openalex.org/", "")
                            works = await self.fetch_author_works(author_openalex_id, max_works=10)

                            for idx, work in enumerate(works):
                                if not work:
                                    continue

                                # Extract venue name
                                primary_location = work.get("primary_location", {})
                                source = primary_location.get("source", {}) if primary_location else {}
                                venue_name = source.get("display_name") if source else None

                                # Extract publication year
                                publication_year = work.get("publication_year")

                                conn.execute(text('''
                                    INSERT INTO core_selected_work (
                                        talent_id, title, publication_year, venue_name,
                                        citation_count, doi, display_order, created_at, updated_at
                                    ) VALUES (
                                        :talent_id, :title, :publication_year, :venue_name,
                                        :citation_count, :doi, :display_order, :now, :now
                                    )
                                '''), {
                                    "talent_id": talent_id,
                                    "title": work.get("title", ""),
                                    "publication_year": publication_year,
                                    "venue_name": venue_name,
                                    "citation_count": work.get("cited_by_count", 0),
                                    "doi": work.get("doi"),
                                    "display_order": idx,
                                    "now": datetime.now()
                                })

                    except Exception as e:
                        print(f"      Error: {e}")

                conn.commit()

        print("\n=== Sync Complete ===")
        print(f"Total authors: {total_authors}")
        print("Role distribution:")
        for role, count in role_counts.items():
            print(f"  {role}: {count}")

    async def sync_works_for_existing_talents(self, batch_size: int = 50):
        """Fetch and insert representative works for existing talents."""
        print("\n=== Syncing Works for Existing Talents ===")

        with self.engine.connect() as conn:
            # Get talents with source_record_id but no works
            result = conn.execute(text('''
                SELECT t.talent_id, t.source_record_id, t.name, t.works_count
                FROM core_talent t
                WHERE t.source_record_id IS NOT NULL
                  AND t.role_type = 'professor'
                  AND t.works_count > 5
                  AND NOT EXISTS (
                      SELECT 1 FROM core_selected_work sw WHERE sw.talent_id = t.talent_id
                  )
                ORDER BY t.works_count DESC
            '''))
            talents = result.fetchall()

            print(f"Found {len(talents)} professors needing works sync")

            total_works = 0
            for i, talent in enumerate(talents):
                talent_id = talent[0]
                source_id = talent[1]
                name = talent[2]
                works_count = talent[3]

                # Extract OpenAlex author ID
                author_openalex_id = source_id.replace("https://openalex.org/", "") if source_id else None
                if not author_openalex_id:
                    continue

                print(f"  [{i+1}/{len(talents)}] {name} ({works_count} works)...")

                try:
                    works = await self.fetch_author_works(author_openalex_id, max_works=10)

                    for idx, work in enumerate(works):
                        if not work:
                            continue

                        primary_location = work.get("primary_location", {})
                        source = primary_location.get("source", {}) if primary_location else {}
                        venue_name = source.get("display_name") if source else None
                        publication_year = work.get("publication_year")

                        conn.execute(text('''
                            INSERT INTO core_selected_work (
                                talent_id, title, publication_year, venue_name,
                                citation_count, doi, display_order, created_at, updated_at
                            ) VALUES (
                                :talent_id, :title, :publication_year, :venue_name,
                                :citation_count, :doi, :display_order, :now, :now
                            )
                        '''), {
                            "talent_id": talent_id,
                            "title": work.get("title", ""),
                            "publication_year": publication_year,
                            "venue_name": venue_name,
                            "citation_count": work.get("cited_by_count", 0),
                            "doi": work.get("doi"),
                            "display_order": idx,
                            "now": datetime.now()
                        })
                        total_works += 1

                    conn.commit()

                    # Rate limiting
                    if (i + 1) % 10 == 0:
                        print("    Pausing to respect rate limits...")
                        await asyncio.sleep(1)

                except Exception as e:
                    print(f"    Error: {e}")

            print("\n=== Works Sync Complete ===")
            print(f"Total works inserted: {total_works}")


async def main():
    """Main sync function."""
    import sys

    sync = OpenAlexSync()

    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--works-only":
            # Only sync works for existing talents
            await sync.sync_works_for_existing_talents()
        else:
            # Full sync
            sync.clean_database()
            school_ids = sync.insert_schools()
            await sync.sync_authors(school_ids, professors_per_school=50, students_per_school=30)
    finally:
        await sync.close()


if __name__ == "__main__":
    asyncio.run(main())
