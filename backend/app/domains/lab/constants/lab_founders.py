"""Founder configuration for lab advisor-tree presentation.

Founder is NOT an imported-data attribute — it is a manually curated
per-lab marker (escape hatch for labs with a clear founder, e.g. LAMDA).
Labs absent from this map render as a neutral parallel forest instead.

Each entry: parent_lab → {"name": <talent record name>, "aliases": [...]}
`aliases` covers advisor-field variants of the founder's name (e.g. the
English form used in student records: "Zhi-Hua Zhou").
"""

from __future__ import annotations

LAB_FOUNDERS: dict[str, dict[str, list[str] | str]] = {
    "南京大学LAMDA实验室": {
        "name": "周志华",
        "aliases": ["Zhi-Hua Zhou"],
    },
}


def founder_for(parent_lab: str) -> tuple[str, set[str]] | None:
    """Return (canonical name, accepted name variants) for a lab, or None."""
    entry = LAB_FOUNDERS.get(parent_lab)
    if not entry:
        return None
    name = entry["name"]
    assert isinstance(name, str)
    aliases = entry.get("aliases", [])
    assert isinstance(aliases, list)
    return name, {name, *aliases}
