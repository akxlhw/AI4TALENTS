"""add_lab_web_site

Revision ID: 051_add_lab_web_site
Revises: 050_add_lab_web_domain
Create Date: 2026-06-29 01:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "051_add_lab_web_site"
down_revision: Union[str, None] = "050_add_lab_web_domain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lw_site_config",
        sa.Column("site_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_code", sa.String(length=50), nullable=False),
        sa.Column("site_name", sa.String(length=255), nullable=False),
        sa.Column("parent_lab_code", sa.String(length=50), nullable=False),
        sa.Column("people_url", sa.String(length=500), nullable=False),
        sa.Column("fetch_mode", sa.String(length=20), nullable=False, server_default="static"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_collected_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("site_id"),
        sa.UniqueConstraint("site_code", name="uq_lw_site_config_site_code"),
    )
    op.create_index("ix_lw_site_config_site_code", "lw_site_config", ["site_code"])
    op.create_index("ix_lw_site_config_parent_lab_code", "lw_site_config", ["parent_lab_code"])

    op.create_table(
        "lw_site_raw_page",
        sa.Column("page_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_code", sa.String(length=50), nullable=False),
        sa.Column("people_url", sa.String(length=500), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("html_hash", sa.String(length=64), nullable=False),
        sa.Column("parsed_persons", sa.JSON(), nullable=True),
        sa.Column("parse_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("llm_model", sa.String(length=100), nullable=True),
        sa.Column("llm_tokens_used", sa.Integer(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("parsed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["site_code"], ["lw_site_config.site_code"]),
        sa.PrimaryKeyConstraint("page_id"),
    )
    op.create_index("ix_lw_site_raw_page_site_code", "lw_site_raw_page", ["site_code"])
    op.create_index("ix_lw_site_raw_page_html_hash", "lw_site_raw_page", ["html_hash"])
    op.create_index("ix_lw_site_raw_page_parse_status", "lw_site_raw_page", ["parse_status"])

    op.execute(
        """
        INSERT INTO lw_site_config (site_code, site_name, parent_lab_code, people_url, fetch_mode, is_active)
        VALUES
          ('stanford_nlp_group', 'Stanford NLP Group', 'stanford_sail', 'https://nlp.stanford.edu/people/', 'static', true),
          ('stanford_snap', 'SNAP Group', 'stanford_sail', 'http://snap.stanford.edu/people.html', 'static', true),
          ('stanford_ermon', 'Ermon Lab', 'stanford_sail', 'https://cs.stanford.edu/~ermon/website/people.html', 'static', true)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_lw_site_raw_page_parse_status", table_name="lw_site_raw_page")
    op.drop_index("ix_lw_site_raw_page_html_hash", table_name="lw_site_raw_page")
    op.drop_index("ix_lw_site_raw_page_site_code", table_name="lw_site_raw_page")
    op.drop_table("lw_site_raw_page")
    op.drop_index("ix_lw_site_config_parent_lab_code", table_name="lw_site_config")
    op.drop_index("ix_lw_site_config_site_code", table_name="lw_site_config")
    op.drop_table("lw_site_config")
