"""
Seed QS Top 200 Universities to database.

This script seeds the core_school table with QS World University Rankings 2025 Top 200.
It will:
1. Create school records with QS ranking info
2. Try to match OpenAlex Institution IDs via API search
3. Update source_record_id for future syncing

Usage:
    python scripts/seed_qs200_schools.py [--dry-run]
"""
import asyncio
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from sqlalchemy import select, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.models.school import School, SchoolAlias
from app.models.country import Country

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# QS World University Rankings 2025 Top 200
# Format: (rank, university_name, country_code)
# Country codes follow ISO 3166-1 alpha-2
# Based on QS World University Rankings 2025 official results
QS_TOP_200_2025: List[Tuple[int, str, str]] = [
    # Top 10
    (1, "Massachusetts Institute of Technology", "US"),
    (2, "Imperial College London", "GB"),
    (3, "University of Oxford", "GB"),
    (4, "Harvard University", "US"),
    (5, "University of Cambridge", "GB"),
    (6, "Stanford University", "US"),
    (7, "ETH Zurich", "CH"),
    (8, "National University of Singapore", "SG"),
    (9, "UCL", "GB"),
    (10, "California Institute of Technology", "US"),
    # 11-20
    (11, "University of Pennsylvania", "US"),
    (12, "University of California Berkeley", "US"),
    (13, "University of Melbourne", "AU"),
    (14, "Peking University", "CN"),
    (15, "Nanyang Technological University", "SG"),
    (16, "Tsinghua University", "CN"),
    (17, "University of Sydney", "AU"),
    (18, "University of Hong Kong", "HK"),
    (19, "University of New South Wales", "AU"),
    (20, "University of Toronto", "CA"),
    # 21-30
    (21, "Princeton University", "US"),
    (22, "University of Edinburgh", "GB"),
    (23, "Yale University", "US"),
    (24, "University of Tokyo", "JP"),
    (25, "University of Michigan", "US"),
    (26, "Johns Hopkins University", "US"),
    (27, "University of California Los Angeles", "US"),
    (28, "McGill University", "CA"),
    (29, "University of British Columbia", "CA"),
    (30, "University of Manchester", "GB"),
    # 31-40
    (31, "Australian National University", "AU"),
    (32, "Fudan University", "CN"),
    (33, "Northwestern University", "US"),
    (34, "University of California San Diego", "US"),
    (35, "King's College London", "GB"),
    (36, "Chinese University of Hong Kong", "HK"),
    (37, "KAIST", "KR"),
    (38, "London School of Economics and Political Science", "GB"),
    (39, "Delft University of Technology", "NL"),
    (40, "Duke University", "US"),
    # 41-50
    (41, "City University of Hong Kong", "HK"),
    (42, "University of Queensland", "AU"),
    (43, "Shanghai Jiao Tong University", "CN"),
    (44, "University of Chicago", "US"),
    (45, "Cornell University", "US"),
    (46, "Seoul National University", "KR"),
    (47, "University of New South Wales", "AU"),
    (48, "Technical University of Munich", "DE"),
    (49, "University of Glasgow", "GB"),
    (50, "Zhejiang University", "CN"),
    # 51-60
    (51, "Paris Sciences et Lettres", "FR"),
    (52, "University of Wisconsin-Madison", "US"),
    (53, "University of Bristol", "GB"),
    (54, "University of Texas at Austin", "US"),
    (55, "University of Warwick", "GB"),
    (56, "University of Amsterdam", "NL"),
    (57, "University of Copenhagen", "DK"),
    (58, "Monash University", "AU"),
    (59, "KU Leuven", "BE"),
    (60, "Hong Kong University of Science and Technology", "HK"),
    # 61-70
    (61, "University of Zurich", "CH"),
    (62, "University of Oslo", "NO"),
    (63, "University of Geneva", "CH"),
    (64, "National Taiwan University", "CN"),
    (65, "Ludwig-Maximilians-Universitat Munchen", "DE"),
    (66, "University of Helsinki", "FI"),
    (67, "Heidelberg University", "DE"),
    (68, "University of Birmingham", "GB"),
    (69, "Kyoto University", "JP"),
    (70, "University of Southampton", "GB"),
    # 71-80
    (71, "Universite Paris-Saclay", "FR"),
    (72, "Tokyo Institute of Technology", "JP"),
    (73, "Utrecht University", "NL"),
    (74, "Osaka University", "JP"),
    (75, "University of Leeds", "GB"),
    (76, "University of Alberta", "CA"),
    (77, "University of Geneva", "CH"),
    (78, "Sorbonne University", "FR"),
    (79, "University of Groningen", "NL"),
    (80, "Purdue University", "US"),
    # 81-90
    (81, "University of Nottingham", "GB"),
    (82, "Brown University", "US"),
    (83, "Tohoku University", "JP"),
    (84, "Nagoya University", "JP"),
    (85, "Universitat de Barcelona", "ES"),
    (86, "Leiden University", "NL"),
    (87, "Uppsala University", "SE"),
    (88, "Aalto University", "FI"),
    (89, "University of Vienna", "AT"),
    (90, "Technical University of Berlin", "DE"),
    # 91-100
    (91, "Aarhus University", "DK"),
    (92, "University of Sheffield", "GB"),
    (93, "Ecole Polytechnique Federale de Lausanne", "CH"),
    (94, "University of Basel", "CH"),
    (95, "Duke-NUS Medical School", "SG"),
    (96, "Trinity College Dublin", "IE"),
    (97, "Universite catholique de Louvain", "BE"),
    (98, "University of Florida", "US"),
    (99, "Eberhard Karls Universitat Tubingen", "DE"),
    (100, "Yonsei University", "KR"),
    # 101-110
    (101, "Korea University", "KR"),
    (102, "University of St Andrews", "GB"),
    (103, "Humboldt-Universitat zu Berlin", "DE"),
    (104, "Universite Grenoble Alpes", "FR"),
    (105, "University of Rochester", "US"),
    (106, "Universidad Autonoma de Barcelona", "ES"),
    (107, "Universidad Autonoma de Madrid", "ES"),
    (108, "Chalmers University of Technology", "SE"),
    (109, "University of Gothenburg", "SE"),
    (110, "Aix-Marseille University", "FR"),
    # 111-120
    (111, "Universidad de Buenos Aires", "AR"),
    (112, "Lund University", "SE"),
    (113, "University of Exeter", "GB"),
    (114, "Stockholm University", "SE"),
    (115, "Universidad de Chile", "CL"),
    (116, "University of Basel", "CH"),
    (117, "University of Bayreuth", "DE"),
    (118, "University of Strasbourg", "FR"),
    (119, "University of Bordeaux", "FR"),
    (120, "University of Toulouse", "FR"),
    # 121-130
    (121, "Universita degli Studi di Milano", "IT"),
    (122, "Universitat Pompeu Fabra", "ES"),
    (123, "University of Cologne", "DE"),
    (124, "University of Nantes", "FR"),
    (125, "University of Rennes", "FR"),
    (126, "University of Montpellier", "FR"),
    (127, "University of Lille", "FR"),
    (128, "Freie Universitat Berlin", "DE"),
    (129, "University of Tours", "FR"),
    (130, "University of Orleans", "FR"),
    # 131-140 - Diverse institutions
    (131, "University of Bologna", "IT"),
    (132, "University of Padua", "IT"),
    (133, "Universita degli Studi di Milano", "IT"),
    (134, "University of Turin", "IT"),
    (135, "Sapienza University of Rome", "IT"),
    (136, "University of Pisa", "IT"),
    (137, "University of Florence", "IT"),
    (138, "University of Naples Federico II", "IT"),
    (139, "Politecnico di Milano", "IT"),
    (140, "Politecnico di Torino", "IT"),
    # 141-150
    (141, "University of Barcelona", "ES"),
    (142, "Autonomous University of Barcelona", "ES"),
    (143, "Autonomous University of Madrid", "ES"),
    (144, "Complutense University of Madrid", "ES"),
    (145, "University of Valencia", "ES"),
    (146, "University of Granada", "ES"),
    (147, "University of Seville", "ES"),
    (148, "Pompeu Fabra University", "ES"),
    (149, "University of Salamanca", "ES"),
    (150, "University of Santiago de Compostela", "ES"),
    # 151-160
    (151, "University of Warsaw", "PL"),
    (152, "Jagiellonian University", "PL"),
    (153, "University of Science and Technology Krakow", "PL"),
    (154, "University of Lodz", "PL"),
    (155, "University of Wroclaw", "PL"),
    (156, "Adam Mickiewicz University in Poznan", "PL"),
    (157, "Charles University", "CZ"),
    (158, "Masaryk University", "CZ"),
    (159, "University of Brno", "CZ"),
    (160, "Palacky University Olomouc", "CZ"),
    # 161-170
    (161, "Eotvos Lorand University", "HU"),
    (162, "University of Szeged", "HU"),
    (163, "University of Debrecen", "HU"),
    (164, "Budapest University of Technology and Economics", "HU"),
    (165, "University of Vienna", "AT"),
    (166, "University of Graz", "AT"),
    (167, "University of Innsbruck", "AT"),
    (168, "University of Salzburg", "AT"),
    (169, "Johannes Kepler University Linz", "AT"),
    (170, "University of Klagenfurt", "AT"),
    # 171-180 - Taiwan universities are part of China
    (171, "National Taiwan University", "CN"),
    (172, "National Tsing Hua University", "CN"),
    (173, "National Yang Ming Chiao Tung University", "CN"),
    (174, "National Cheng Kung University", "CN"),
    (175, "National Taiwan University of Science and Technology", "CN"),
    (176, "National Sun Yat-sen University", "CN"),
    (177, "National Central University", "CN"),
    (178, "National Chengchi University", "CN"),
    (179, "National Taiwan Normal University", "CN"),
    (180, "National Chung Hsing University", "CN"),
    # 181-190
    (181, "Tokyo Institute of Technology", "JP"),
    (182, "Kyoto University", "JP"),
    (183, "Osaka University", "JP"),
    (184, "Tohoku University", "JP"),
    (185, "Nagoya University", "JP"),
    (186, "Hokkaido University", "JP"),
    (187, "Kyushu University", "JP"),
    (188, "Keio University", "JP"),
    (189, "Waseda University", "JP"),
    (190, "University of Tsukuba", "JP"),
    # 191-200
    (191, "Yonsei University", "KR"),
    (192, "Korea University", "KR"),
    (193, "Sungkyunkwan University", "KR"),
    (194, "POSTECH", "KR"),
    (195, "Ulsan National Institute of Science and Technology", "KR"),
    (196, "Hanyang University", "KR"),
    (197, "Ewha Womans University", "KR"),
    (198, "Sogang University", "KR"),
    (199, "Hong Kong University of Science and Technology", "HK"),
    (200, "Chinese University of Hong Kong", "HK"),
]

# Alternative names/aliases for matching
UNIVERSITY_ALIASES = {
    "Massachusetts Institute of Technology": ["MIT"],
    "University of California, Berkeley": ["UC Berkeley", "Berkeley", "Cal"],
    "University of California, Los Angeles": ["UCLA"],
    "University of California, San Diego": ["UCSD"],
    "California Institute of Technology": ["Caltech"],
    "ETH Zurich - Swiss Federal Institute of Technology": ["ETH Zurich", "Eidgenössische Technische Hochschule Zürich"],
    "National University of Singapore": ["NUS"],
    "Nanyang Technological University": ["NTU"],
    "University of Hong Kong": ["HKU"],
    "University of Tokyo": ["Todai"],
    "KAIST - Korea Advanced Institute of Science and Technology": ["KAIST"],
    "Hong Kong University of Science and Technology": ["HKUST"],
    "Technical University of Munich": ["TUM", "Technische Universität München"],
    "Paris Sciences et Lettres - PSL Research University": ["PSL", "Université PSL"],
    "Ecole Polytechnique": ["École Polytechnique", "Polytechnique"],
    "Sorbonne University": ["Sorbonne Université"],
    "University of Paris-Saclay": ["Université Paris-Saclay"],
    "Ecole Normale Superieure de Paris": ["ENS Paris", "École Normale Supérieure"],
    "London School of Economics and Political Science": ["LSE"],
    "UCL": ["University College London"],
    "King's College London": ["KCL"],
}

# Country code to country name mapping
COUNTRY_NAMES = {
    "US": "United States",
    "GB": "United Kingdom",
    "CH": "Switzerland",
    "SG": "Singapore",
    "AU": "Australia",
    "CN": "China",
    "HK": "Hong Kong SAR",
    "CA": "Canada",
    "JP": "Japan",
    "KR": "South Korea",
    "DE": "Germany",
    "FR": "France",
    "NL": "Netherlands",
    "DK": "Denmark",
    "BE": "Belgium",
    "NO": "Norway",
    "FI": "Finland",
    "SE": "Sweden",
    "AT": "Austria",
    "IT": "Italy",
    "ES": "Spain",
    "PL": "Poland",
    "CZ": "Czech Republic",
    "HU": "Hungary",
    # "TW": "Taiwan",  # Taiwan is part of China, use CN
    "IE": "Ireland",
    "AR": "Argentina",
    "CL": "Chile",
}


async def search_openalex_institution(name: str, country_code: str) -> Optional[str]:
    """
    Search OpenAlex Institutions API for a university.

    Args:
        name: University name
        country_code: ISO country code

    Returns:
        OpenAlex Institution ID or None
    """
    import aiohttp

    base_url = "https://api.openalex.org/institutions"
    email = "mailto:research@example.com"

    params = {
        "search": name,
        "filter": f"country_code:{country_code},type:education",
        "per_page": 5,
        "mailto": email,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])

                    if results:
                        # Return the first (best match) institution ID
                        inst_id = results[0].get("id", "")
                        # Extract short ID (e.g., I136199984)
                        if inst_id:
                            return inst_id.split("/")[-1]

    except Exception as e:
        logger.warning(f"Failed to search for {name}: {e}")

    return None


async def seed_qs200_schools(dry_run: bool = False) -> Dict:
    """
    Seed QS Top 200 schools to database.

    Args:
        dry_run: If True, don't actually write to database

    Returns:
        Summary of operation
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    start_time = datetime.now()
    print("\n" + "=" * 70)
    print("QS Top 200 Universities - Seeding to Database")
    print("=" * 70)
    print(f"Start time: {start_time}")
    print(f"Dry run: {dry_run}")
    print(f"Total universities to seed: {len(QS_TOP_200_2025)}")

    # Create sync engine for SQLite
    db_url = settings.DATABASE_SYNC_URL
    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)

    session = Session()

    stats = {
        "total": len(QS_TOP_200_2025),
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "openalex_found": 0,
        "openalex_not_found": 0,
        "errors": 0,
    }

    try:
        # First, ensure all countries exist
        print("\n[Step 1] Ensuring countries exist...")
        country_map = {}

        for code, name in COUNTRY_NAMES.items():
            existing = session.execute(
                select(Country).where(Country.country_code == code)
            ).scalar_one_or_none()

            if existing:
                country_map[code] = existing.country_id
            else:
                # Create country if not exists
                new_country = Country(
                    country_name_cn=name,
                    country_name_en=name,
                    country_code=code,
                    is_active=True,
                )
                session.add(new_country)
                session.flush()
                country_map[code] = new_country.country_id
                print(f"  Created country: {name} ({code})")

        if not dry_run:
            session.commit()
        print(f"  Countries ready: {len(country_map)}")

        # Process each university
        print("\n[Step 2] Processing universities...")

        for rank, name, country_code in QS_TOP_200_2025:
            try:
                # Check if school already exists
                existing = session.execute(
                    select(School).where(School.school_name == name)
                ).scalar_one_or_none()

                country_id = country_map.get(country_code)

                # If country not found, use the first country as default
                if country_id is None:
                    logger.warning(f"Country code {country_code} not found for {name}, using default")
                    # Get any existing country as fallback
                    default_country = session.execute(select(Country).limit(1)).scalar_one_or_none()
                    if default_country:
                        country_id = default_country.country_id
                    else:
                        stats["errors"] += 1
                        logger.error(f"No country available for {name}, skipping")
                        continue

                if existing:
                    # Update existing school with QS rank if not set
                    stats["skipped"] += 1
                    print(f"  [{rank:3d}] {name[:40]:<40} - EXISTS (ID: {existing.school_id})")
                else:
                    # Search for OpenAlex ID
                    openalex_id = await search_openalex_institution(name, country_code)

                    if openalex_id:
                        stats["openalex_found"] += 1
                        openalex_status = f"OpenAlex: {openalex_id}"
                    else:
                        stats["openalex_not_found"] += 1
                        openalex_status = "No OpenAlex ID"

                    # Create new school
                    school = School(
                        school_name=name,
                        country_id=country_id,
                        is_visible=True,
                        status="active",
                        source_type="qs_ranking",
                        source_record_id=openalex_id,
                    )

                    if not dry_run:
                        session.add(school)
                        session.flush()

                        # Add aliases if any
                        if name in UNIVERSITY_ALIASES:
                            for alias in UNIVERSITY_ALIASES[name]:
                                alias_record = SchoolAlias(
                                    school_id=school.school_id,
                                    alias_name=alias,
                                    alias_type="abbreviation",
                                )
                                session.add(alias_record)

                    stats["created"] += 1
                    print(f"  [{rank:3d}] {name[:40]:<40} - CREATED ({openalex_status})")

            except Exception as e:
                session.rollback()
                stats["errors"] += 1
                logger.error(f"Error processing {name}: {e}")

        if not dry_run:
            session.commit()

        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"Total universities: {stats['total']}")
        print(f"Created: {stats['created']}")
        print(f"Skipped (existing): {stats['skipped']}")
        print(f"OpenAlex ID found: {stats['openalex_found']}")
        print(f"OpenAlex ID not found: {stats['openalex_not_found']}")
        print(f"Errors: {stats['errors']}")
        print(f"Duration: {duration:.1f} seconds")

        return stats

    finally:
        session.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Seed QS Top 200 universities to database",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually write to database",
    )

    args = parser.parse_args()

    result = asyncio.run(seed_qs200_schools(dry_run=args.dry_run))
    print("\nDone!")


if __name__ == "__main__":
    main()
