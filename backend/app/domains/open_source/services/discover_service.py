"""Auto-discover well-known open-source projects by tech direction.

Background task pattern mirrors lab's prefetch_background_service: status
(including full results) persisted in sys_config as JSON, heartbeat allows
re-running after dead tasks, one concurrent run enforced via status check.

Flow: for each selected tech direction, search GitHub for repos with
stars >= threshold using seeded keyword queries. Results are deduped
across directions (a repo hit by multiple directions merges its
direction_codes), flagged whether it already exists in os_repo_config,
and stored in the status blob for preview. Importing is a separate
explicit step that reuses batch_create_repo_configs.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.database import AsyncSessionLocal
from app.domains.open_source.constants.discover_keywords import (
    DIRECTION_SEARCH_KEYWORDS,
)
from app.domains.shared.constants.tech_taxonomy import (
    DIRECTION_TO_DOMAIN,
    DIRECTION_TO_ELEMENT,
    DOMAIN_MIN_STARS_OVERRIDE,
)
from app.domains.shared.services.config_service import ConfigService

logger = logging.getLogger(__name__)

DISCOVER_STATUS_KEY = "os_discover_status"

# A running task whose heartbeat is older than this is considered dead
# (e.g. after a service restart) and a new run may start.
HEARTBEAT_TIMEOUT_SECONDS = 300

# Search API allows 30 req/min authenticated → 2.5s between searches.
SEARCH_INTERVAL_SECONDS = 2.5

# Cap per direction (repos per search query merged, then top-N by stars).
MAX_REPOS_PER_DIRECTION = 20

DEFAULT_STATUS: dict[str, Any] = {
    "status": "idle",  # idle | running | completed | error
    "processed": 0,
    "total": 0,
    "current": "",
    "found": 0,
    "errors": 0,
    "heartbeat_at": "",
    "results": [],
    "started_at": "",
    "finished_at": "",
    "params": {},
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_heartbeat_alive(heartbeat_at: str | None) -> bool:
    if not heartbeat_at:
        return False
    try:
        heartbeat = datetime.fromisoformat(heartbeat_at)
    except (ValueError, TypeError):
        return False
    if heartbeat.tzinfo is None:
        heartbeat = heartbeat.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - heartbeat < timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)


async def load_status(config_service: ConfigService) -> dict[str, Any]:
    status = await config_service.get_value(DISCOVER_STATUS_KEY, default=None, use_cache=False)
    if status is None:
        return DEFAULT_STATUS.copy()
    return {**DEFAULT_STATUS, **status}


async def save_status(config_service: ConfigService, status: dict[str, Any]) -> None:
    await config_service.set_value(DISCOVER_STATUS_KEY, status, config_type="json")
    await config_service.session.commit()


async def get_discovery_status() -> dict[str, Any]:
    """Current discovery status + results (for API polling)."""
    async with AsyncSessionLocal() as session:
        config_service = ConfigService(session)
        return await load_status(config_service)


async def start_discovery(direction_codes: list[str], min_stars: int) -> dict[str, Any]:
    """Launch the background discovery task. Raises ConflictError if running.

    Returns the initial status dict.
    """
    from app.core.exceptions import ConflictError

    async with AsyncSessionLocal() as session:
        config_service = ConfigService(session)
        status = await load_status(config_service)
        if status["status"] == "running" and is_heartbeat_alive(status.get("heartbeat_at")):
            raise ConflictError("A discovery task is already running")

        # Keep only directions that have keyword seeds
        effective = [d for d in direction_codes if d in DIRECTION_SEARCH_KEYWORDS]

        status.update(
            {
                "status": "running",
                "processed": 0,
                "total": len(effective),
                "current": "starting",
                "found": 0,
                "errors": 0,
                "results": [],
                "heartbeat_at": utc_now_iso(),
                "started_at": utc_now_iso(),
                "finished_at": "",
                "params": {"direction_codes": effective, "min_stars": min_stars},
            }
        )
        await save_status(config_service, status)

    asyncio.create_task(run_discovery(effective, min_stars))
    return status


async def run_discovery(direction_codes: list[str], min_stars: int) -> None:
    """Background coroutine: search GitHub per direction, persist results."""
    from app.domains.open_source.services.github_client import GitHubClient
    from app.domains.shared.services.config_service import ConfigService

    async with AsyncSessionLocal() as session:
        config_service = ConfigService(session)
        status = await load_status(config_service)
        status["status"] = "running"
        status["heartbeat_at"] = utc_now_iso()
        await save_status(config_service, status)
        logger.info(
            "[Discover] started: %s directions, min_stars=%s", len(direction_codes), min_stars
        )

        # repo_full_name → result record (dedup across directions)
        merged: dict[str, dict[str, Any]] = {}

        try:
            github_config = await config_service.get_github_config()
            token = github_config.tokens if github_config.tokens else None

            async with GitHubClient(token=token) as client:
                first_search = True
                for direction in direction_codes:
                    queries = DIRECTION_SEARCH_KEYWORDS.get(direction, [])
                    direction_hits: dict[str, dict[str, Any]] = {}
                    # Per-domain threshold override replaces the global floor
                    # for domains whose ecosystems sit below it (robotics etc.)
                    domain = DIRECTION_TO_DOMAIN.get(direction, "")
                    threshold = DOMAIN_MIN_STARS_OVERRIDE.get(domain, min_stars)

                    for query in queries:
                        if not first_search:
                            await asyncio.sleep(SEARCH_INTERVAL_SECONDS)
                        first_search = False

                        full_query = f"{query} stars:>={threshold}"
                        try:
                            resp = await client.search_repositories(full_query, per_page=30)
                        except Exception as e:
                            status["errors"] += 1
                            logger.warning("[Discover] search failed for %r: %s", full_query, e)
                            continue

                        for item in resp.get("items", []):
                            if item.get("fork"):
                                continue
                            stars = item.get("stargazers_count", 0) or 0
                            if stars < threshold:
                                continue
                            full_name = item.get("full_name", "")
                            if not full_name:
                                continue
                            direction_hits[full_name] = {
                                "repo_full_name": full_name,
                                "display_name": item.get("name", ""),
                                "description": (item.get("description") or "")[:500],
                                "language": item.get("language"),
                                "stars": stars,
                                "html_url": item.get("html_url", ""),
                                "direction_codes": [direction],
                            }

                    # Keep top-N by stars for this direction, merge into global set
                    top = sorted(direction_hits.values(), key=lambda r: -r["stars"])[
                        :MAX_REPOS_PER_DIRECTION
                    ]
                    for rec in top:
                        name = rec["repo_full_name"]
                        if name in merged:
                            if direction not in merged[name]["direction_codes"]:
                                merged[name]["direction_codes"].append(direction)
                        else:
                            merged[name] = rec

                    status["processed"] += 1
                    status["current"] = direction
                    status["found"] = len(merged)
                    status["heartbeat_at"] = utc_now_iso()
                    # Persist partial results so a crash still leaves what we found
                    status["results"] = list(merged.values())
                    await save_status(config_service, status)

            # Flag repos that already exist in os_repo_config
            from sqlalchemy import select

            from app.domains.open_source.models.open_source import OSRepoConfig

            names = list(merged.keys())
            existing: set[str] = set()
            for i in range(0, len(names), 500):
                chunk = names[i : i + 500]
                rows = await session.execute(
                    select(OSRepoConfig.repo_full_name).where(
                        OSRepoConfig.repo_full_name.in_(chunk)
                    )
                )
                existing.update(r[0] for r in rows.all())

            results = list(merged.values())
            for rec in results:
                rec["exists_in_config"] = rec["repo_full_name"] in existing
                # Element codes (union across hit directions) power the import
                # tagging — tech_element valid values are element codes (v2).
                elements: list[str] = []
                for d in rec["direction_codes"]:
                    element = DIRECTION_TO_ELEMENT.get(d)
                    if element and element not in elements:
                        elements.append(element)
                rec["element_codes"] = elements
            results.sort(key=lambda r: -r["stars"])

            status.update(
                {
                    "status": "completed",
                    "current": "done",
                    "found": len(results),
                    "results": results,
                    "finished_at": utc_now_iso(),
                    "heartbeat_at": utc_now_iso(),
                }
            )
            await save_status(config_service, status)
            logger.info("[Discover] completed: %d repos found", len(results))

        except asyncio.CancelledError:
            status.update(
                {"status": "error", "current": "cancelled", "heartbeat_at": utc_now_iso()}
            )
            await save_status(config_service, status)
            raise
        except Exception:
            logger.exception("[Discover] background task failed")
            status.update({"status": "error", "current": "failed", "heartbeat_at": utc_now_iso()})
            await save_status(config_service, status)
            raise


async def import_discovered(
    selection: list[dict[str, Any]], created_by: int | None = None
) -> dict[str, list]:
    """Import selected discovered repos via the existing batch-create path.

    ``selection`` items: {"repo_full_name": str, "tech_element": list[str]}.
    Delegates to OSCollectionService.batch_create_repo_configs, which fetches
    fresh metadata from GitHub and skips existing configs.
    """
    from app.domains.open_source.services.os_collection_service import OSCollectionService

    async with AsyncSessionLocal() as session:
        service = OSCollectionService(session)
        results: dict[str, list] = {"created": [], "skipped": [], "failed": []}
        for item in selection:
            elements = item.get("tech_element") or ["ai"]
            result = await service.batch_create_repo_configs(
                repo_inputs=[item["repo_full_name"]],
                tech_element=elements,
                created_by=created_by,
            )
            for key in results:
                results[key].extend(result.get(key, []))
        await session.commit()
        return results
