"""Taxonomy v2: 10 domains / 34 elements / 75 directions (platform-wide).

Replaces the legacy 6-domain taxonomy (领域→要素→方向). Preserves direction_id
for kept/renamed codes so talent_tech_tag / os_repo_config references stay
valid; merges legacy directions (refs moved, old rows deleted); remaps
industry_position JSON codes, os_repo_config.tech_element to element codes,
and denormalized tech_domain_id FKs. Single source of truth:
app/domains/shared/constants/tech_taxonomy.py

Revision ID: 062
Revises: 061
Create Date: 2026-08-15
"""

from alembic import op

from app.domains.shared.constants.tech_taxonomy import (
    DOMAIN_MIN_STARS_OVERRIDE,  # noqa: F401  (re-exported for discover seeds)
    OLD_DIRECTION_REMAP,
    OLD_DOMAIN_ELEMENT_FALLBACK,
    OLD_REPO_ELEMENT_MAP,
    TECH_DIRECTIONS,
    TECH_DOMAINS,
    TECH_ELEMENTS,
)

# revision identifiers, used by Alembic.
revision = "062"
down_revision = "061"
branch_labels = None
depends_on = None

# Renamed-in-place: old code → new code (row keeps its id)
_RENAMED_DIRECTIONS = {"cv": "cv_applications", "speech": "speech_models", "multimodal": "vlm"}

# Merged: old code exists in OLD_DIRECTION_REMAP but is NOT preserved/renamed
_PRESERVED = {
    old
    for old, new in OLD_DIRECTION_REMAP.items()
    if old == new or old in _RENAMED_DIRECTIONS
}
_MERGED_DIRECTIONS = [old for old in OLD_DIRECTION_REMAP if old not in _PRESERVED]


def upgrade() -> None:
    # ── 1. element columns ──
    op.execute("ALTER TABLE core_tech_direction ADD COLUMN IF NOT EXISTS element_code VARCHAR(50)")
    op.execute("ALTER TABLE core_tech_direction ADD COLUMN IF NOT EXISTS element_name VARCHAR(100)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_core_tech_direction_element_code "
        "ON core_tech_direction (element_code)"
    )

    # ── 2. upsert 10 domains (legacy robotics code kept, updated in place) ──
    for i, dom in enumerate(TECH_DOMAINS, start=1):
        op.execute(
            f"""
            INSERT INTO core_tech_domain (domain_code, domain_name, domain_name_en, sort_order, is_enabled)
            VALUES ('{dom["code"]}', '{_esc(dom["name"])}', '{_esc(dom["name_en"])}', {i}, true)
            ON CONFLICT (domain_code) DO UPDATE SET
                domain_name = EXCLUDED.domain_name,
                domain_name_en = EXCLUDED.domain_name_en,
                sort_order = EXCLUDED.sort_order
            """
        )

    # ── 3a. rename legacy direction codes in place (keep ids) ──
    for old_code, new_code in _RENAMED_DIRECTIONS.items():
        op.execute(
            f"UPDATE core_tech_direction SET direction_code = '{new_code}' "
            f"WHERE direction_code = '{old_code}'"
        )

    # ── 3b. upsert all 75 directions ──
    for i, (code, name, name_en, element) in enumerate(TECH_DIRECTIONS, start=1):
        el = TECH_ELEMENTS[element]
        op.execute(
            f"""
            INSERT INTO core_tech_direction
                (direction_code, direction_name, direction_name_en,
                 element_code, element_name, tech_domain_id, sort_order, is_enabled)
            VALUES (
                '{code}', '{_esc(name)}', '{_esc(name_en)}',
                '{element}', '{_esc(el["name"])}',
                (SELECT tech_domain_id FROM core_tech_domain WHERE domain_code = '{el["domain"]}'),
                {i}, true
            )
            ON CONFLICT (direction_code) DO UPDATE SET
                direction_name = EXCLUDED.direction_name,
                direction_name_en = EXCLUDED.direction_name_en,
                element_code = EXCLUDED.element_code,
                element_name = EXCLUDED.element_name,
                tech_domain_id = EXCLUDED.tech_domain_id,
                sort_order = EXCLUDED.sort_order
            """
        )

    # ── 4. merge legacy directions: move refs then delete ──
    for old_code in _MERGED_DIRECTIONS:
        new_code = OLD_DIRECTION_REMAP[old_code]
        for table in ("core_talent_tech_tag", "os_repo_config"):
            op.execute(
                f"UPDATE {table} SET tech_direction_id = ("
                f"  SELECT tech_direction_id FROM core_tech_direction WHERE direction_code = '{new_code}'"
                f") WHERE tech_direction_id IN ("
                f"  SELECT tech_direction_id FROM core_tech_direction WHERE direction_code = '{old_code}'"
                f")"
            )
    merged_list = ", ".join(f"'{c}'" for c in _MERGED_DIRECTIONS)
    op.execute(f"DELETE FROM core_tech_direction WHERE direction_code IN ({merged_list})")

    # ── 5. industry_position JSON direction-code remap (renamed + merged) ──
    for old_code, new_code in OLD_DIRECTION_REMAP.items():
        if old_code == new_code:
            continue
        op.execute(
            f"""
            UPDATE industry_position SET tech_direction_codes = (
                SELECT COALESCE(jsonb_agg(
                    CASE WHEN el = '{old_code}' THEN '{new_code}' ELSE el END
                ), '[]'::jsonb)
                FROM jsonb_array_elements_text(tech_direction_codes::jsonb) AS el
            )::json
            WHERE tech_direction_codes::jsonb @> jsonb_build_array('{old_code}')
            """
        )

    # ── 6. os_repo_config.tech_element → element codes ──
    # 6a. explicit per-repo map (43 seeded repos)
    for full_name, element in OLD_REPO_ELEMENT_MAP.items():
        op.execute(
            f"""
            UPDATE os_repo_config SET tech_element = jsonb_build_array('{element}')
            WHERE repo_full_name = '{full_name}'
              AND NOT tech_element::jsonb ? '{element}'
            """
        )
    # 6b. fallback by legacy domain code (user-created repos)
    for old_domain, element in OLD_DOMAIN_ELEMENT_FALLBACK.items():
        op.execute(
            f"""
            UPDATE os_repo_config SET tech_element = jsonb_build_array('{element}')
            WHERE tech_element::jsonb @> jsonb_build_array('{old_domain}')
            """
        )

    # ── 7. re-parent any remaining legacy-domain directions ──
    # Covers rows NOT in the v1 seed: user-created directions and the legacy
    # *-DEFAULT aggregate directions (which carry ~52k talent tags from the
    # academic tech-belong phase). DEFAULT rows are kept but disabled so the
    # tags stay queryable while the taxonomy UI stays clean.
    _legacy_to_new = {
        "ai": ("ai_models", "models"),
        "data_science": ("modeling_simulation", "sci_compute"),
        "networks": ("communications", "protocols"),
        "systems": ("computing", "cloud_native"),
        "security": ("trusted_security", "sys_sec"),
        "robotics": ("robotics", "robot_control"),
    }
    for old_dom, (new_dom, element) in _legacy_to_new.items():
        op.execute(
            f"""
            UPDATE core_tech_direction SET
                tech_domain_id = (SELECT tech_domain_id FROM core_tech_domain WHERE domain_code = '{new_dom}'),
                element_code = '{element}'
            WHERE tech_domain_id IN (
                SELECT tech_domain_id FROM core_tech_domain WHERE domain_code = '{old_dom}'
            )
            """
        )
    # Fill element_name for all rows carrying an element_code but no name yet
    for element, meta in TECH_ELEMENTS.items():
        op.execute(
            f"""
            UPDATE core_tech_direction SET element_name = '{_esc(meta["name"])}'
            WHERE element_code = '{element}' AND (element_name IS NULL OR element_name = '')
            """
        )
    # Disable the legacy DEFAULT aggregate directions (data preserved)
    op.execute(
        "UPDATE core_tech_direction SET is_enabled = false "
        "WHERE direction_code LIKE '%-DEFAULT'"
    )

    # ── 7b. sync denormalized tag.tech_domain_id to the direction's new domain ──
    op.execute(
        """
        UPDATE core_talent_tech_tag t SET tech_domain_id = (
            SELECT d.tech_domain_id FROM core_tech_direction d
            WHERE d.tech_direction_id = t.tech_direction_id
        )
        """
    )
    # 7c. dedup tags: direction merges may give one talent two rows pointing
    # at the same new direction (uq_talent_tech_direction). Keep the row with
    # the highest confidence (tie-break: highest tag_id).
    op.execute(
        """
        DELETE FROM core_talent_tech_tag t
        USING core_talent_tech_tag t2
        WHERE t.talent_id = t2.talent_id
          AND t.tech_direction_id = t2.tech_direction_id
          AND t.tag_id <> t2.tag_id
          AND (
            t.confidence_score < t2.confidence_score
            OR (t.confidence_score = t2.confidence_score AND t.tag_id < t2.tag_id)
          )
        """
    )

    # ── 7d. remap denormalized tech_domain_id in academic config/sync tables ──
    # These tables carry a direct legacy-domain FK; point them at successors.
    for table in ("config_venue_tech_binding", "rel_author_tech_belong", "sync_collect_task"):
        for old_dom, (new_dom, _element) in _legacy_to_new.items():
            op.execute(
                f"UPDATE {table} SET tech_domain_id = ("
                f"  SELECT tech_domain_id FROM core_tech_domain WHERE domain_code = '{new_dom}'"
                f") WHERE tech_domain_id = ("
                f"  SELECT tech_domain_id FROM core_tech_domain WHERE domain_code = '{old_dom}'"
                f")"
            )

    # ── 8. drop the 5 legacy domains (robotics kept; all directions re-parented) ──
    op.execute(
        "DELETE FROM core_tech_domain WHERE domain_code IN "
        "('ai', 'data_science', 'networks', 'systems', 'security')"
    )


def downgrade() -> None:
    """Forward-only: the legacy 6-domain taxonomy is not restored.

    Restoring would require re-splitting element tags back to domain codes
    and re-creating deleted direction rows — lossy for the ai→ai_models/
    ai_apps split. Restore from a database backup if truly needed.
    """
    pass


def _esc(text: str) -> str:
    """Escape single quotes for inline SQL strings."""
    return text.replace("'", "''")
