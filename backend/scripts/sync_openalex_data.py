"""
OpenAlex data sync script - Fetches real data from OpenAlex API.
Includes professors, students, and graduates.
"""
import asyncio
import httpx
import random
from datetime import datetime
from typing import Dict, List
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

    async def fetch_authors_by_institution(
        self,
        institution_id: str,
        max_authors: int = 100,
        min_works: int = None
    ) -> List[Dict]:
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
    ) -> List[Dict]:
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

    def determine_role_type(self, author: Dict) -> tuple:
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

    def extract_topics(self, author: Dict) -> List[str]:
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

    def insert_schools(self) -> Dict[str, int]:
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

    async def sync_authors(self, school_ids: Dict[str, int], professors_per_school: int = 50, students_per_school: int = 30):
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
            print(f"    Fetching professors...")
            prof_authors = await self.fetch_authors_by_institution(
                openalex_id,
                max_authors=professors_per_school,
                min_works=30  # At least 30 works for professors
            )

            # 2. Fetch students (low works count)
            print(f"    Fetching students...")
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
                        total_authors += 1
                    except Exception as e:
                        print(f"      Error: {e}")

                conn.commit()

        print(f"\n=== Sync Complete ===")
        print(f"Total authors: {total_authors}")
        print(f"Role distribution:")
        for role, count in role_counts.items():
            print(f"  {role}: {count}")


async def main():
    """Main sync function."""
    sync = OpenAlexSync()

    try:
        sync.clean_database()
        school_ids = sync.insert_schools()
        await sync.sync_authors(school_ids, professors_per_school=50, students_per_school=30)
    finally:
        await sync.close()


if __name__ == "__main__":
    asyncio.run(main())
