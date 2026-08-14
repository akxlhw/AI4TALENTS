"""Industry domain status enums and labels.

Candidate link status and position status values per
docs/v5.0.0/02-技术设计.md §3.1/§3.3.
"""

# Position lifecycle (no physical delete; open → closed → archived)
POSITION_STATUSES: list[str] = ["open", "closed", "archived"]
POSITION_STATUS_LABELS: dict[str, str] = {
    "open": "在招",
    "closed": "已关闭",
    "archived": "已归档",
}

# Candidate recruiting status on a position-talent link
CANDIDATE_STATUSES: list[str] = ["new", "connected", "terminated"]
CANDIDATE_STATUS_LABELS: dict[str, str] = {
    "new": "新候选人",
    "connected": "已连接",
    "terminated": "已终止",
}

# Known source platforms (informational; import does not hard-reject others)
SOURCE_PLATFORMS: list[str] = ["maimai", "linkedin"]

# Sentinel for "no batch" (batch IS NULL) in batch-management APIs — a real
# batch name can never be this value because path params can't carry NULL
NULL_BATCH_SENTINEL = "__none__"
