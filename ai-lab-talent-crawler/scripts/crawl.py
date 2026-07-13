"""Helper functions for ai-lab-talent-crawler skill.

These are utilities the agent (or a human) can call to:
- load_labs: read labs.yaml and optionally filter by name/domain
- write_jsonl: write persons to a validated JSONL file
- load_existing_persons: read a prior JSONL for resume/dedup (#2)
- generate_report: write a human-readable collection report
- check_browser_service: async probe Camofox/kimi-webbridge availability (#6)

The agent's core logic (explore + extract) is driven by the LLM reading
SKILL.md + references; this script handles the mechanical I/O parts.
"""
from __future__ import annotations

import asyncio
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
import yaml


def slugify(name: str) -> str:
    """Convert a lab name to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "_", name.strip())
    slug = slug.strip("_")
    return slug.lower() if slug.isascii() else slug


def load_labs(labs_file: str, match: str | None = None) -> list[dict[str, Any]]:
    """Load labs from labs.yaml. If match is given, filter by name/domain substring."""
    with open(labs_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    labs = data.get("labs", [])
    if match:
        m_lower = match.lower()
        labs = [
            lab
            for lab in labs
            if m_lower in lab.get("name", "").lower()
            or m_lower in lab.get("domain", "").lower()
        ]
    return labs


def write_jsonl(
    persons: list[dict[str, Any]],
    output_dir: str,
    lab_slug: str,
    date_str: str,
) -> str:
    """Write persons to output/<lab_slug>/_<date>.jsonl.

    Validates each entry: must have non-empty name. Drops entries without name.
    """
    lab_dir = Path(output_dir) / lab_slug
    lab_dir.mkdir(parents=True, exist_ok=True)
    path = lab_dir / f"_{date_str}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for person in persons:
            name = person.get("name")
            if not name or not str(name).strip():
                continue  # drop nameless entries
            f.write(json.dumps(person, ensure_ascii=False))
            f.write("\n")
    return str(path)


def load_existing_persons(
    output_dir: str, lab_slug: str
) -> list[dict[str, Any]]:
    """Read the most recent prior JSONL for this lab, for resume/dedup (#2).

    Returns a list of person dicts from the newest _*.jsonl file in
    output/<lab_slug>/. Returns [] if no prior file exists.

    The agent uses this to skip bio follow-up for persons already collected
    in a prior run (matched by name + lab_name), enabling multi-session
    collection of large labs without re-visiting every bio.
    """
    lab_dir = Path(output_dir) / lab_slug
    if not lab_dir.exists():
        return []
    jsonl_files = sorted(lab_dir.glob("_*.jsonl"), key=lambda p: p.name, reverse=True)
    if not jsonl_files:
        return []
    persons: list[dict[str, Any]] = []
    with open(jsonl_files[0], encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                persons.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return persons


def generate_report(
    persons: list[dict[str, Any]],
    output_dir: str,
    lab_name: str,
    lab_domain: str,
    date_str: str,
    notes: str = "",
) -> str:
    """Generate a human-readable collection report markdown."""
    total = len(persons)
    role_counts = Counter(p.get("role_section", "Unknown") for p in persons)
    cohort_known = sum(1 for p in persons if "cohort_year" in p)
    email_known = sum(1 for p in persons if "email" in p)

    lines = [
        f"# {lab_name} 采集报告 — {date_str}",
        "",
        "## 采集概况",
        f"- 目标实验室: {lab_name} ({lab_domain})",
        f"- 采集时间: {date_str}",
        f"- 总人数: {total}",
        "",
        "## 角色分布",
    ]
    for role, count in role_counts.most_common():
        lines.append(f"  - {role}: {count}")
    lines.extend(
        [
            "",
            "## 数据质量提示",
            f"- 博士生届别覆盖率: {cohort_known}/{total} ({(100 * cohort_known // total) if total else 0}%)"
            if total
            else "- 博士生届别覆盖率: 0/0",
            f"- 有邮箱: {email_known}/{total}",
        ]
    )
    if notes:
        lines.extend(["", "## 异常与人工待确认", notes])
    report = "\n".join(lines)

    lab_slug = slugify(lab_name)
    lab_dir = Path(output_dir) / lab_slug
    lab_dir.mkdir(parents=True, exist_ok=True)
    report_path = lab_dir / f"_report_{date_str}.md"
    report_path.write_text(report, encoding="utf-8")
    return report


async def check_browser_service() -> str | None:
    """Async probe browser automation services. Returns which one is available, or None.

    Tries Camofox first (:9377), then kimi-webbridge (:10086). Uses httpx async
    to avoid blocking the event loop in async agent runtimes (#6).
    """
    targets = [
        ("camofox", "http://localhost:9377/tabs?userId=probe"),
        ("kimi-webbridge", "http://127.0.0.1:10086"),
    ]
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, url in targets:
            try:
                resp = await client.get(url)
                if resp.status_code < 500:
                    return name
            except Exception:
                continue
    return None
