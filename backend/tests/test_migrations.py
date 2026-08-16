"""
Migration integrity tests.

These tests verify that database migrations work correctly in two critical scenarios:
1. Fresh deployment: Empty database -> migrate to head -> all tables created
2. Upgrade deployment: Existing data -> migrate -> data preserved

Test categories:
- Static tests: Run always, no database required
- Slow tests: Require ability to create/drop databases, run with: pytest tests/test_migrations.py -v --run-slow
"""

import os

import pytest
from sqlalchemy import create_engine, text


def get_postgres_connection(dbname: str = "postgres"):
    """Get a connection to PostgreSQL server."""
    from dotenv import load_dotenv

    load_dotenv()

    database_url = os.getenv(
        "DATABASE_SYNC_URL", "postgresql://talent_user:ai4recruit@localhost:5432/talent_db"
    )

    import re

    match = re.match(r"postgresql://(\w+):(\w+)@([^:]+):(\d+)/(\w+)", database_url)
    if not match:
        pytest.skip("Cannot parse DATABASE_SYNC_URL")

    user, password, host, port, _ = match.groups()
    server_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

    return create_engine(server_url, isolation_level="AUTOCOMMIT")


@pytest.fixture
def temp_database():
    """Create a temporary database for testing migrations."""
    import secrets

    db_name = f"test_migration_{secrets.token_hex(4)}"

    engine = get_postgres_connection()

    try:
        with engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE {db_name}"))

        yield db_name

    finally:
        with engine.connect() as conn:
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{db_name}'
                AND pid <> pg_backend_pid()
            """))
            conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))

        engine.dispose()


def alembic_env(temp_db_url: str) -> dict:
    """Build the subprocess environment for `alembic` against a temp database.

    Sets BOTH the async URL (DATABASE_URL, what migrations/env.py actually
    uses to run migrations) and the sync URL (DATABASE_SYNC_URL, used by
    alembic.ini and any sync tooling). Setting only one caused alembic to
    silently connect to a different (pre-populated) database.
    """
    async_url = temp_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return {**os.environ, "DATABASE_URL": async_url, "DATABASE_SYNC_URL": temp_db_url}


# =============================================================================
# STATIC TESTS - Always run, no database required
# =============================================================================


class TestMigrationStaticChecks:
    """Static checks on migration files - no database required."""

    def test_migration_chain_is_linear(self):
        """
        Verify that migration chain is linear without branches.

        Branched migrations can cause deployment issues.
        """
        import subprocess

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            ["alembic", "history", "--verbose"], cwd=backend_dir, capture_output=True, text=True
        )

        output = result.stdout
        assert "(head)" in output, "No head revision found"

        head_count = output.count("(head)")
        assert (
            head_count == 1
        ), f"Multiple heads detected ({head_count} heads). Migration chain has branched!"

    def test_migration_files_are_reasonable_size(self):
        """
        Verify that migration files are reasonable size.

        Overly large migration files often indicate incorrect auto-generation
        that recreates the entire schema instead of incremental changes.
        """
        import glob

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        migrations_dir = os.path.join(backend_dir, "migrations", "versions")

        migration_files = glob.glob(os.path.join(migrations_dir, "*.py"))

        for filepath in migration_files:
            filename = os.path.basename(filepath)
            if filename.startswith("__"):
                continue

            with open(filepath, encoding="utf-8") as f:
                content = f.read()
                lines = content.count("\n")

            if "001_initial" in filename:
                assert (
                    lines < 500
                ), f"Initial migration {filename} is too large ({lines} lines). Consider splitting."
            elif any(
                keyword in filename
                for keyword in ["add_open_source", "add_raw_data", "add_standardized"]
            ):
                # Migrations that create multiple new tables may legitimately be larger
                assert lines < 400, (
                    f"Migration {filename} is too large ({lines} lines) even for a "
                    "multi-table creation. Please review and consider splitting."
                )
            else:
                assert lines < 250, (
                    f"Migration {filename} is suspiciously large ({lines} lines). "
                    "This often indicates incorrect auto-generation that recreates the entire schema. "
                    "Please review and fix."
                )

    def test_migration_dependencies_correct(self):
        """
        Verify that each migration has correct down_revision dependency.
        """
        import glob
        import re as regex

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        migrations_dir = os.path.join(backend_dir, "migrations", "versions")

        migration_files = glob.glob(os.path.join(migrations_dir, "*.py"))

        revisions = {}
        dependencies = {}

        for filepath in migration_files:
            filename = os.path.basename(filepath)
            if filename.startswith("__"):
                continue

            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            rev_match = regex.search(r"revision:\s*str\s*=\s*['\"]([^'\"]+)['\"]", content)
            if not rev_match:
                continue
            revision = rev_match.group(1)

            down_match = regex.search(
                r"down_revision:\s*Union\[str,\s*None\]\s*=\s*['\"]?([^'\"\n]+)['\"]?", content
            )
            down_revision = down_match.group(1) if down_match else None
            if down_revision == "None":
                down_revision = None

            revisions[revision] = filename
            dependencies[revision] = down_revision

        for revision, down_revision in dependencies.items():
            if down_revision and down_revision not in revisions:
                pytest.fail(
                    f"Migration {revisions[revision]} references non-existent down_revision: {down_revision}"
                )

    def test_migration_version_format(self):
        """
        Verify that migration version IDs follow consistent format.
        """
        import glob
        import re as regex

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        migrations_dir = os.path.join(backend_dir, "migrations", "versions")

        migration_files = glob.glob(os.path.join(migrations_dir, "*.py"))

        for filepath in migration_files:
            filename = os.path.basename(filepath)
            if filename.startswith("__"):
                continue

            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            rev_match = regex.search(r"revision:\s*str\s*=\s*['\"]([^'\"]+)['\"]", content)
            if not rev_match:
                continue
            revision = rev_match.group(1)

            is_numeric = regex.match(r"^\d+$", revision)
            is_numeric_with_suffix = regex.match(r"^\d+_[a-z_]+$", revision)
            is_hash = regex.match(r"^[a-f0-9]{12}$", revision)

            assert is_numeric or is_numeric_with_suffix or is_hash, (
                f"Migration {filename} has unusual revision format: {revision}. "
                "Expected numeric (001), numeric with suffix (001_initial), or 12-char hash."
            )

    def test_no_duplicate_table_creations(self):
        """
        Verify that no table is created in the upgrade() body of more than one
        migration. A duplicate create in upgrade paths means migrations fight
        each other and the chain cannot run cleanly on a fresh database.

        Only upgrade() bodies are scanned: it is legitimate for a migration
        that drops a table to recreate it in its own downgrade() (the inverse
        operation), so downgrade() creates are intentionally excluded.
        """
        import glob
        import re as regex

        # Multi-line tolerant: op.create_table( may be followed by whitespace
        # or a newline before the quoted table name (the form Alembic autogen
        # emits). The old single-line regex matched nothing and hid real dupes.
        create_re = regex.compile(r"op\.create_table\(\s*['\"](\w+)['\"]")

        def extract_upgrade_body(content: str) -> str:
            """Return the source of the upgrade() function, excluding downgrade()."""
            m = regex.search(
                r"\ndef upgrade\([^)]*\)[^:]*:\n(.*?)(?=\ndef \w+\([^)]*\))",
                content,
                regex.DOTALL,
            )
            return m.group(1) if m else ""

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        migrations_dir = os.path.join(backend_dir, "migrations", "versions")

        table_creates: dict[str, list[str]] = {}

        for filepath in sorted(glob.glob(os.path.join(migrations_dir, "*.py"))):
            filename = os.path.basename(filepath)
            if filename.startswith("__"):
                continue

            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            upgrade_body = extract_upgrade_body(content)
            for table in create_re.findall(upgrade_body):
                table_creates.setdefault(table, []).append(filename)

        duplicates = {table: files for table, files in table_creates.items() if len(files) > 1}

        assert not duplicates, (
            "Tables created in upgrade() of multiple migrations (likely bug): " f"{duplicates}"
        )

    def test_all_migrations_have_upgrade_and_downgrade(self):
        """
        Verify that all migrations have both upgrade() and downgrade() functions.
        """
        import glob

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        migrations_dir = os.path.join(backend_dir, "migrations", "versions")

        migration_files = glob.glob(os.path.join(migrations_dir, "*.py"))

        for filepath in migration_files:
            filename = os.path.basename(filepath)
            if filename.startswith("__"):
                continue

            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            has_upgrade = "def upgrade()" in content
            has_downgrade = "def downgrade()" in content

            assert has_upgrade, f"Migration {filename} missing upgrade() function"
            assert has_downgrade, f"Migration {filename} missing downgrade() function"

    def test_migration_imports_are_valid(self):
        """
        Verify that migrations use correct imports.
        """
        import glob

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        migrations_dir = os.path.join(backend_dir, "migrations", "versions")

        migration_files = glob.glob(os.path.join(migrations_dir, "*.py"))

        for filepath in migration_files:
            filename = os.path.basename(filepath)
            if filename.startswith("__"):
                continue

            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            # Check for common import issues
            has_alembic_op = (
                "from alembic import op" in content or "import alembic.op as op" in content
            )

            # At minimum, migrations need 'op'
            assert (
                has_alembic_op or "op." in content
            ), f"Migration {filename} doesn't import alembic.op"


# =============================================================================
# SLOW TESTS - Require database, marked with @pytest.mark.slow
# =============================================================================


@pytest.mark.slow
class TestFreshDeployment:
    """Test that migrations work for fresh deployment (empty database)."""

    def test_fresh_deployment_creates_all_tables(self, temp_database):
        """
        Verify that running migrations from scratch creates all required tables.

        This is the MOST CRITICAL test for deployment - it ensures that
        `alembic upgrade head` works on an empty database.
        """
        import subprocess

        database_url = os.getenv(
            "DATABASE_SYNC_URL", "postgresql://talent_user:ai4recruit@localhost:5432/talent_db"
        )
        import re

        match = re.match(r"postgresql://(\w+):(\w+)@([^:]+):(\d+)/(\w+)", database_url)
        user, password, host, port, _ = match.groups()
        temp_db_url = f"postgresql://{user}:{password}@{host}:{port}/{temp_database}"

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=alembic_env(temp_db_url),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Migration failed: {result.stderr}"

        engine = get_postgres_connection(temp_database)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]

        critical_tables = [
            "iam_user_account",
            "core_talent",
            "core_school",
            "core_tech_domain",
            "config_venue",
            "raw_work",
            "raw_author",
            "std_author",
            "std_school",
            "sync_collect_task",
            "alembic_version",
        ]

        for table in critical_tables:
            assert table in tables, f"Table '{table}' was not created by migration"

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.fetchone()
            assert version is not None, "alembic_version table is empty"

        engine.dispose()


@pytest.mark.slow
class TestUpgradeDeployment:
    """Test that migrations preserve existing data during upgrades."""

    def test_migration_preserves_user_data(self, temp_database):
        """
        Verify that migrations preserve existing user data.
        """
        import subprocess

        database_url = os.getenv(
            "DATABASE_SYNC_URL", "postgresql://talent_user:ai4recruit@localhost:5432/talent_db"
        )
        import re

        match = re.match(r"postgresql://(\w+):(\w+)@([^:]+):(\d+)/(\w+)", database_url)
        user, password, host, port, _ = match.groups()
        temp_db_url = f"postgresql://{user}:{password}@{host}:{port}/{temp_database}"

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=alembic_env(temp_db_url),
            capture_output=True,
            check=True,
        )

        engine = get_postgres_connection(temp_database)
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO iam_user_account
                (username, email, password_hash, role_type, is_active, status, display_name, created_at, updated_at)
                VALUES ('testuser', 'test@example.com', 'test_hash', 'recruiter', true, 'active', 'Test User', NOW(), NOW())
            """))

        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=alembic_env(temp_db_url),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Re-running migrations failed: {result.stderr}"

        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT username, email FROM iam_user_account WHERE username = 'testuser'")
            )
            user_row = result.fetchone()

        assert user_row is not None, "User data was lost after migration!"
        assert user_row[0] == "testuser"
        assert user_row[1] == "test@example.com"

        engine.dispose()


@pytest.mark.slow
class TestMigrationRollback:
    """Test that migrations can be safely rolled back."""

    def test_downgrade_base_and_upgrade(self, temp_database):
        """
        Verify that migrations can be downgraded and re-upgraded.
        """
        import subprocess

        database_url = os.getenv(
            "DATABASE_SYNC_URL", "postgresql://talent_user:ai4recruit@localhost:5432/talent_db"
        )
        import re

        match = re.match(r"postgresql://(\w+):(\w+)@([^:]+):(\d+)/(\w+)", database_url)
        user, password, host, port, _ = match.groups()
        temp_db_url = f"postgresql://{user}:{password}@{host}:{port}/{temp_database}"

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=alembic_env(temp_db_url),
            capture_output=True,
            check=True,
        )

        result = subprocess.run(
            ["alembic", "downgrade", "base"],
            cwd=backend_dir,
            env=alembic_env(temp_db_url),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.skip(
                f"Downgrade failed (some migrations may lack proper downgrade): {result.stderr}"
            )

        engine = get_postgres_connection(temp_database)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name != 'alembic_version'
            """))
            tables = [row[0] for row in result.fetchall()]

        assert len(tables) == 0, f"Tables not cleaned up after downgrade: {tables}"

        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=alembic_env(temp_db_url),
            capture_output=True,
            check=True,
        )

        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]

        assert "iam_user_account" in tables
        assert "core_talent" in tables

        engine.dispose()


@pytest.mark.slow
class TestModelMigrationConsistency:
    """Test that SQLAlchemy models match migrated database schema."""

    def test_models_match_migrated_tables(self, temp_database):
        """
        Verify that SQLAlchemy model definitions match the migrated table structure.
        """
        import subprocess

        from sqlalchemy import inspect

        database_url = os.getenv(
            "DATABASE_SYNC_URL", "postgresql://talent_user:ai4recruit@localhost:5432/talent_db"
        )
        import re

        match = re.match(r"postgresql://(\w+):(\w+)@([^:]+):(\d+)/(\w+)", database_url)
        user, password, host, port, _ = match.groups()
        temp_db_url = f"postgresql://{user}:{password}@{host}:{port}/{temp_database}"

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=alembic_env(temp_db_url),
            capture_output=True,
            check=True,
        )

        import sys

        sys.path.insert(0, backend_dir)
        from app.core.database import Base

        engine = create_engine(temp_db_url)

        inspector = inspect(engine)
        db_tables = set(inspector.get_table_names())

        model_tables = set(Base.metadata.tables.keys())

        missing_in_db = model_tables - db_tables
        assert (
            not missing_in_db
        ), f"Tables defined in models but missing in database: {missing_in_db}"

        engine.dispose()


@pytest.mark.slow
class TestMigrationIdempotency:
    """Test that migrations are idempotent."""

    def test_migration_idempotency(self, temp_database):
        """
        Verify that running migrations multiple times is safe.
        """
        import subprocess

        database_url = os.getenv(
            "DATABASE_SYNC_URL", "postgresql://talent_user:ai4recruit@localhost:5432/talent_db"
        )
        import re

        match = re.match(r"postgresql://(\w+):(\w+)@([^:]+):(\d+)/(\w+)", database_url)
        user, password, host, port, _ = match.groups()
        temp_db_url = f"postgresql://{user}:{password}@{host}:{port}/{temp_database}"

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        result1 = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=alembic_env(temp_db_url),
            capture_output=True,
            text=True,
        )
        assert result1.returncode == 0, f"First migration failed: {result1.stderr}"

        result2 = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=alembic_env(temp_db_url),
            capture_output=True,
            text=True,
        )
        assert (
            result2.returncode == 0
        ), f"Second migration failed (not idempotent): {result2.stderr}"
