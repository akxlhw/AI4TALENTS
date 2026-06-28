"""add_lab_web_domain

Revision ID: 050_add_lab_web_domain
Revises: 049_add_genealogy_tables
Create Date: 2026-06-28 23:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "050_add_lab_web_domain"
down_revision: Union[str, None] = "049_add_genealogy_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lw_lab_registry",
        sa.Column("lab_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lab_code", sa.String(length=50), nullable=False),
        sa.Column("lab_name", sa.String(length=255), nullable=False),
        sa.Column("lab_name_en", sa.String(length=255), nullable=True),
        sa.Column("institution", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=50), nullable=False),
        sa.Column("people_url", sa.String(length=500), nullable=False),
        sa.Column("collector_class", sa.String(length=255), nullable=True),
        sa.Column("fetch_mode", sa.String(length=20), nullable=False, server_default="static"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_collected_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("lab_id"),
        sa.UniqueConstraint("lab_code", name="uq_lw_lab_registry_lab_code"),
    )
    op.create_index("ix_lw_lab_registry_lab_code", "lw_lab_registry", ["lab_code"])

    op.create_table(
        "lw_raw_person",
        sa.Column("raw_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lab_id", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("name_raw", sa.String(length=255), nullable=False),
        sa.Column("title_raw", sa.String(length=255), nullable=True),
        sa.Column("email_raw", sa.String(length=255), nullable=True),
        sa.Column("homepage_url", sa.String(length=500), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("collect_task_id", sa.Integer(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["lab_id"], ["lw_lab_registry.lab_id"]),
        sa.PrimaryKeyConstraint("raw_id"),
    )
    op.create_index("ix_lw_raw_person_lab_id", "lw_raw_person", ["lab_id"])
    op.create_index("ix_lw_raw_person_collect_task_id", "lw_raw_person", ["collect_task_id"])
    op.create_index("ix_lw_raw_person_content_hash", "lw_raw_person", ["content_hash"])

    op.create_table(
        "lw_collect_task",
        sa.Column("task_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("lab_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_step", sa.String(length=100), nullable=True),
        sa.Column("total_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["lab_id"], ["lw_lab_registry.lab_id"]),
        sa.ForeignKeyConstraint(["created_by"], ["iam_user_account.user_id"]),
        sa.PrimaryKeyConstraint("task_id"),
    )
    op.create_index("ix_lw_collect_task_lab_id", "lw_collect_task", ["lab_id"])
    op.create_index("ix_lw_collect_task_status", "lw_collect_task", ["status"])

    # Seed the lab registry (SAIL implemented, rest pending collector_class=null).
    op.execute(
        """
        INSERT INTO lw_lab_registry (lab_code, lab_name, institution, country, people_url, collector_class, fetch_mode, is_active)
        VALUES
          ('stanford_sail', 'Stanford AI Lab', 'Stanford University', 'US', 'https://ai.stanford.edu/people/', 'labs.stanford_sail.StanfordSailCollector', 'static', true),
          ('mit_csail', 'MIT CSAIL', 'MIT', 'US', 'https://www.csail.mit.edu/people/', NULL, 'static', true),
          ('deepmind', 'Google DeepMind', 'Google', 'UK', 'https://www.deepmind.com/people', NULL, 'dynamic', true),
          ('fair', 'FAIR', 'Meta', 'US', 'https://ai.meta.com/crew/', NULL, 'dynamic', true),
          ('openai', 'OpenAI', 'OpenAI', 'US', 'https://openai.com/people/', NULL, 'dynamic', true),
          ('anthropic', 'Anthropic', 'Anthropic', 'US', 'https://www.anthropic.com/people', NULL, 'dynamic', true),
          ('msr', 'Microsoft Research', 'Microsoft', 'US', 'https://www.microsoft.com/en-us/research/people/', NULL, 'static', true),
          ('bair', 'Berkeley AI Research', 'UC Berkeley', 'US', 'https://bair.berkeley.edu/people/', NULL, 'static', true),
          ('baai', '北京智源人工智能研究院', 'BAAI', 'CN', 'https://www.baai.ac.cn/en/about-us', NULL, 'static', true),
          ('tsinghua_air', '清华大学人工智能研究院', 'Tsinghua University', 'CN', 'https://www.ai.tsinghua.edu.cn/en/', NULL, 'static', true)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_lw_collect_task_status", table_name="lw_collect_task")
    op.drop_index("ix_lw_collect_task_lab_id", table_name="lw_collect_task")
    op.drop_table("lw_collect_task")
    op.drop_index("ix_lw_raw_person_content_hash", table_name="lw_raw_person")
    op.drop_index("ix_lw_raw_person_collect_task_id", table_name="lw_raw_person")
    op.drop_index("ix_lw_raw_person_lab_id", table_name="lw_raw_person")
    op.drop_table("lw_raw_person")
    op.drop_index("ix_lw_lab_registry_lab_code", table_name="lw_lab_registry")
    op.drop_table("lw_lab_registry")
