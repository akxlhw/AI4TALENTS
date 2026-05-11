"""
Open Source Talent API endpoints.

Backward-compatibility shim — the actual endpoints have been split into:
  - repo_config.py   (CRUD for /repo-configs)
  - collection.py    (repo-triggered collection + task management)
  - developers.py    (developer, repository, search endpoints)
  - favourites.py    (favourites + talent pools)
  - stats.py         (stats, JD match, embeddings)

Import ``router`` from this module or from the package's ``__init__``.
"""

from app.domains.open_source.api import router  # noqa: F401

__all__ = ["router"]
