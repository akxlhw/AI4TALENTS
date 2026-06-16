#!/usr/bin/env python3
"""
AI4TALENT Database Deployment Script
在新安装 PostgreSQL 后运行此脚本，一键部署开发数据库

前置条件:
  1. PostgreSQL 18 已安装 (默认路径 D:\\Program Files\\PostgreSQL\\18)
  2. pgvector 已编译 (位于 D:\\AI\\pgvector)
  3. 后端依赖已安装 (uv sync)

用法:
  cd D:\\AI\\AI4TALENT\\backend
  uv run python scripts/ops/deploy_database.py
  uv run python scripts/ops/deploy_database.py --skip-migration-fix
"""

import getpass
import os
import shutil
import subprocess
import sys

# ============================================================
# 配置
# ============================================================
PG_HOME = r"D:\Program Files\PostgreSQL\18"
PG_BIN = os.path.join(PG_HOME, "bin")
PGVECTOR_SRC = r"D:\AI\pgvector"
DB_USER = "talent_user"
DB_PASS = "ai4recruit"
DB_NAME = "talent_db"
DB_TEST = "talent_db_test"
SUPERUSER = "postgres"
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MIG_DIR = os.path.join(BACKEND_DIR, "migrations", "versions")


def ok(msg: str):
    print(f"  [\033[0;32mOK\033[0m] {msg}")


def warn(msg: str):
    print(f"  [\033[1;33mWARN\033[0m] {msg}")


def fail(msg: str):
    print(f"  [\033[0;31mERROR\033[0m] {msg}")
    sys.exit(1)


def run_psql(sql: str, dbname: str = "postgres") -> subprocess.CompletedProcess:
    """Execute SQL via psql."""
    env = os.environ.copy()
    if "PGPASSWORD" in os.environ:
        env["PGPASSWORD"] = os.environ["PGPASSWORD"]
    cmd = [
        os.path.join(PG_BIN, "psql.exe"),
        "-U", SUPERUSER,
        "-d", dbname,
        "-c", sql,
    ]
    return subprocess.run(cmd, capture_output=True, env=env, encoding="utf-8", errors="replace")


def run_cmd(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", **kwargs)


def main():
    skip_fix = "--skip-migration-fix" in sys.argv

    print("=" * 60)
    print("AI4TALENT Database Deployment")
    print("=" * 60)

    # ---- 输入超级用户密码 ----
    if not os.environ.get("PGPASSWORD"):
        pg_pass = getpass.getpass(f"\n请输入 PostgreSQL 超级用户 ({SUPERUSER}) 的密码: ")
        os.environ["PGPASSWORD"] = pg_pass

    # ---- Step 0: 检查 PostgreSQL 是否运行 ----
    print("\nStep 0: Check PostgreSQL service")
    pg_isready = os.path.join(PG_BIN, "pg_isready.exe")
    result = run_cmd([pg_isready])
    if result.returncode == 0:
        ok("PostgreSQL is running")
    else:
        warn("PostgreSQL not running, trying to start...")
        start_result = run_cmd(["net", "start", "postgresql-x64-18"], shell=True)
        if start_result.returncode != 0:
            fail("Failed to start PostgreSQL. Run: net start postgresql-x64-18")
        import time
        time.sleep(2)
        result2 = run_cmd([pg_isready])
        if result2.returncode == 0:
            ok("PostgreSQL started")
        else:
            fail("PostgreSQL still not responding")

    # ---- Step 1: 安装 pgvector ----
    print("\nStep 1: Install pgvector extension")
    if os.path.isdir(PGVECTOR_SRC):
        lib_dir = os.path.join(PG_HOME, "lib")
        ext_dir = os.path.join(PG_HOME, "share", "extension")
        # DLL
        for f in ["vector.dll"]:
            src = os.path.join(PGVECTOR_SRC, f)
            if os.path.exists(src):
                shutil.copy2(src, lib_dir, follow_symlinks=True)
                ok(f"Copied {f}")
        # control file
        ctrl = os.path.join(PGVECTOR_SRC, "vector.control")
        if os.path.exists(ctrl):
            shutil.copy2(ctrl, ext_dir, follow_symlinks=True)
            ok("Copied vector.control")
        # SQL files are in sql/ subdirectory
        sql_dir = os.path.join(PGVECTOR_SRC, "sql")
        if os.path.isdir(sql_dir):
            for f in os.listdir(sql_dir):
                if f.startswith("vector") and f.endswith(".sql"):
                    shutil.copy2(os.path.join(sql_dir, f), ext_dir, follow_symlinks=True)
            ok("Copied SQL install scripts from sql/")
    else:
        warn(f"pgvector source not found at {PGVECTOR_SRC}, skipping")

    # ---- Step 2: 创建用户和数据库 ----
    print("\nStep 2: Create user and databases")
    r = run_psql(f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{DB_USER}') THEN
                CREATE ROLE {DB_USER} WITH LOGIN PASSWORD '{DB_PASS}' SUPERUSER;
            END IF;
        END $$;
    """)
    if r.returncode == 0:
        ok(f"User '{DB_USER}' ready")
    else:
        fail(f"Create user failed: {(r.stderr or r.stdout or '').strip()[:200]}")

    for db in [DB_NAME, DB_TEST]:
        r = run_psql(f"SELECT count(*) FROM pg_database WHERE datname = '{db}'")
        if "1" in r.stdout:
            ok(f"Database '{db}' ready (exists)")
        else:
            r2 = run_psql(f"CREATE DATABASE {db} OWNER {DB_USER}")
            if r2.returncode == 0:
                ok(f"Database '{db}' created")
            else:
                fail(f"Create database {db} failed: {(r2.stderr or r2.stdout or '').strip()[:200]}")

    # ---- Step 3: 创建扩展 ----
    print("\nStep 3: Create extensions")
    for db in [DB_NAME, DB_TEST]:
        r = run_psql(
            'CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS pg_trgm; CREATE EXTENSION IF NOT EXISTS "uuid-ossp";',
            dbname=db,
        )
        if r.returncode == 0:
            ok(f"Extensions installed on {db}")
        else:
            fail(f"Extensions failed on {db}: {(r.stderr or r.stdout or '').strip()[:200]}")

    # ---- Step 4: 修复迁移文件 (PG18 兼容性) ----
    if not skip_fix:
        print("\nStep 4: Patch migration files for PG18 compatibility")
        patch_migrations()
        ok("Migration patches applied")
    else:
        print("\nStep 4: Skipped (--skip-migration-fix)")

    # ---- Step 5: 运行数据库迁移 ----
    print("\nStep 5: Run Alembic migrations")
    r = run_cmd(["uv", "run", "python", "-m", "alembic", "upgrade", "head"], cwd=BACKEND_DIR)
    if r.returncode == 0:
        ok("All migrations applied")
    else:
        # 打印最后几行关键错误
        lines = r.stderr.strip().split("\n") if r.stderr else r.stdout.strip().split("\n")
        for line in lines[-5:]:
            print(f"    {line}")
        fail("Migration failed")

    # ---- Step 6: 初始化种子数据 ----
    print("\nStep 6: Seed initial data")
    r = run_cmd(["uv", "run", "python", "scripts/data/init_system.py", "--full", "--force"], cwd=BACKEND_DIR)
    if r.returncode == 0:
        ok("Seed data initialized")
    else:
        fail(f"Seed failed: {(r.stderr or r.stdout or '').strip()[:200]}")

    # ---- 完成 ----
    print()
    print("=" * 60)
    print("Database deployment complete!")
    print("=" * 60)
    print()
    print("  Admin: admin / admin123")
    print("  Demo:  demo / demo123")
    print()
    print(f"  Database: {DB_NAME}")
    print(f"  Test DB:  {DB_TEST}")
    print()


def patch_migrations():
    """Fix information_schema queries for PG18 compatibility."""

    # ---- 012: column_exists 函数 ----
    f012 = os.path.join(MIG_DIR, "012_add_venue_config.py")
    if os.path.exists(f012):
        content = open(f012, encoding="utf-8").read()
        old = '''def column_exists(conn, table_name, column_name):
    """Check if a column exists in a table (PostgreSQL compatible)."""
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = :table AND column_name = :column
    """), {"table": table_name, "column": column_name})
    return result.fetchone() is not None'''
        new = '''def column_exists(conn, table_name, column_name):
    """Check if a column exists in a table (PostgreSQL compatible)."""
    result = conn.execute(sa.text(
        f"SELECT attname FROM pg_catalog.pg_attribute "
        f"WHERE attrelid = \'{table_name}\'::regclass AND attname = :column "
        f"AND attnum > 0 AND NOT attisdropped"
    ), {"column": column_name})
    return result.fetchone() is not None'''
        if old in content:
            content = content.replace(old, new)
            open(f012, "w", encoding="utf-8").write(content)
            print("  Patched 012_add_venue_config.py")
        else:
            print("  012 already patched or different, skipping")

    # ---- 022: 所有 information_schema 查询 ----
    f022 = os.path.join(MIG_DIR, "022_remove_country_table.py")
    if os.path.exists(f022):
        content = open(f022, encoding="utf-8").read()
        if "information_schema" in content:
            # FK check
            content = content.replace(
                """SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_name = 'core_school'
            AND constraint_type = 'FOREIGN KEY'
            AND constraint_name = 'fk_core_school_country_id_core_country'""",
                """SELECT conname FROM pg_catalog.pg_constraint
            WHERE conrelid = 'core_school'::regclass
            AND contype = 'f'
            AND conname = 'fk_core_school_country_id_core_country'""",
            )
            # Column check
            content = content.replace(
                """SELECT column_name FROM information_schema.columns
            WHERE table_name = 'core_school' AND column_name = 'country_id'""",
                """SELECT attname FROM pg_catalog.pg_attribute
            WHERE attrelid = 'core_school'::regclass AND attname = 'country_id'
            AND attnum > 0 AND NOT attisdropped""",
            )
            # FK lookup in other tables
            content = content.replace(
                """SELECT tc.table_name, tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND kcu.table_name != 'core_school'
        AND kcu.column_name = 'country_id'""",
                """SELECT cl.relname AS table_name, con.conname AS constraint_name
        FROM pg_catalog.pg_constraint con
        JOIN pg_catalog.pg_class cl ON con.conrelid = cl.oid
        JOIN pg_catalog.pg_namespace ns ON cl.relnamespace = ns.oid
        WHERE con.contype = 'f'
        AND ns.nspname = 'public'
        AND cl.relname != 'core_school'
        AND EXISTS (
            SELECT 1 FROM pg_catalog.pg_attribute a
            WHERE a.attrelid = con.conrelid
            AND a.attnum = ANY(con.conkey)
            AND a.attname = 'country_id'
        )""",
            )
            # Column lookup in other tables
            content = content.replace(
                """SELECT table_name FROM information_schema.columns
        WHERE column_name = 'country_id' AND table_name != 'core_school'
        AND table_schema = 'public'""",
                """SELECT c.relname AS table_name
        FROM pg_catalog.pg_attribute a
        JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
        JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
        WHERE a.attname = 'country_id' AND c.relname NOT IN ('core_school', 'core_country')
        AND n.nspname = 'public' AND c.relkind = 'r'
        AND a.attnum > 0 AND NOT a.attisdropped""",
            )
            # Table existence check
            content = content.replace(
                """SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'core_country'""",
                """SELECT c.relname FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = 'public' AND c.relname = 'core_country'""",
            )
            open(f022, "w", encoding="utf-8").write(content)
            print("  Patched 022_remove_country_table.py")
        else:
            print("  022 already patched, skipping")

    # ---- 025: search_vector 列检查 ----
    f025 = os.path.join(MIG_DIR, "025_add_fulltext_search.py")
    if os.path.exists(f025):
        content = open(f025, encoding="utf-8").read()
        old = """SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'search_talent_document'
                    AND column_name = 'search_vector'"""
        new = """SELECT 1 FROM pg_catalog.pg_attribute
                    WHERE attrelid = 'search_talent_document'::regclass
                    AND attname = 'search_vector'
                    AND attnum > 0 AND NOT attisdropped"""
        if old in content:
            content = content.replace(old, new)
            open(f025, "w", encoding="utf-8").write(content)
            print("  Patched 025_add_fulltext_search.py")
        else:
            print("  025 already patched, skipping")


if __name__ == "__main__":
    main()
