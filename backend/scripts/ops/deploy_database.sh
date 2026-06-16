#!/usr/bash
# ============================================================
# AI4TALENT Database Deployment Script
# 在新安装 PostgreSQL 后运行此脚本，一键部署开发数据库
#
# 前置条件:
#   1. PostgreSQL 18 已安装 (默认路径 D:\Program Files\PostgreSQL\18)
#   2. pgvector 已编译 (位于 D:\AI\pgvector)
#   3. 后端依赖已安装 (uv sync)
#
# 用法:
#   cd D:\AI\AI4TALENT\backend
#   bash scripts/ops/deploy_database.sh           # 完整部署
#   bash scripts/ops/deploy_database.sh --skip-migration-fix  # 跳过迁移文件修复
# ============================================================

set -e

# ---- 配置 ----
PG_HOME="D:/Program Files/PostgreSQL/18"
PG_BIN="$PG_HOME/bin"
PGDATA="$PG_HOME/data"
PGVECTOR_SRC="D:/AI/pgvector"
DB_USER="talent_user"
DB_PASS="ai4recruit"
DB_NAME="talent_db"
DB_TEST="talent_db_test"
SUPERUSER="postgres"
BACKEND_DIR="D:/AI/AI4TALENT/backend"

# 提示输入超级用户密码
if [[ -z "$PGPASSWORD" ]]; then
    echo ""
    read -sp "请输入 PostgreSQL 超级用户 ($SUPERUSER) 的密码: " PGPASSWORD
    echo ""
    export PGPASSWORD
fi

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

SKIP_FIX=false
if [[ "$1" == "--skip-migration-fix" ]]; then
    SKIP_FIX=true
fi

echo "============================================================"
echo "AI4TALENT Database Deployment"
echo "============================================================"

# ---- Step 0: 检查 PostgreSQL 是否运行 ----
echo ""
echo "Step 0: Check PostgreSQL service"
if "$PG_BIN/pg_isready.exe" -q 2>/dev/null; then
    info "PostgreSQL is running"
else
    warn "PostgreSQL is not running, trying to start..."
    net start postgresql-x64-18 2>/dev/null || error "Failed to start PostgreSQL. Run: net start postgresql-x64-18"
    sleep 2
    if "$PG_BIN/pg_isready.exe" -q 2>/dev/null; then
        info "PostgreSQL started"
    else
        error "PostgreSQL still not responding"
    fi
fi

# ---- Step 1: 安装 pgvector ----
echo ""
echo "Step 1: Install pgvector extension"
if [[ -d "$PGVECTOR_SRC" ]]; then
    # 复制 DLL
    cp -v "$PGVECTOR_SRC/vector.dll" "$PG_HOME/lib/" 2>/dev/null && info "Copied vector.dll" || warn "vector.dll copy skipped (may already exist)"
    # 复制 control 和 SQL 文件
    cp -v "$PGVECTOR_SRC/vector.control" "$PG_HOME/share/extension/" 2>/dev/null && info "Copied vector.control" || warn "vector.control copy skipped"
    cp -v "$PGVECTOR_SRC/vector"*.sql "$PGHOME/share/extension/" 2>/dev/null && info "Copied vector SQL files" || warn "vector SQL files copy skipped"
else
    warn "pgvector source not found at $PGVECTOR_SRC, skipping"
fi

# ---- Step 2: 创建用户和数据库 ----
echo ""
echo "Step 2: Create user and databases"

# 创建用户（如果不存在）
"$PG_BIN/psql.exe" -U $SUPERUSER -d postgres -c \
    "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASS' SUPERUSER; END IF; END \$\$;" \
    && info "User '$DB_USER' ready"

# 创建数据库（如果不存在）
for db in $DB_NAME $DB_TEST; do
    "$PG_BIN/psql.exe" -U $SUPERUSER -d postgres -c \
        "SELECT 'CREATE DATABASE $db OWNER $DB_USER' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\\gexec" \
        && info "Database '$db' ready"
done

# ---- Step 3: 创建扩展 ----
echo ""
echo "Step 3: Create extensions"
for db in $DB_NAME $DB_TEST; do
    "$PG_BIN/psql.exe" -U $SUPERUSER -d $db -c \
        "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS pg_trgm; CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" \
        && info "Extensions installed on $db"
done

# ---- Step 4: 修复迁移文件 (PG18 information_schema 兼容性) ----
if [[ "$SKIP_FIX" == "false" ]]; then
    echo ""
    echo "Step 4: Patch migration files for PG18 compatibility"

    MIG_DIR="$BACKEND_DIR/migrations/versions"

    # 修复 012: column_exists 函数
    python3 -c "
import re
f = '$MIG_DIR/012_add_venue_config.py'
content = open(f, 'r', encoding='utf-8').read()
old = '''def column_exists(conn, table_name, column_name):
    \"\"\"Check if a column exists in a table (PostgreSQL compatible).\"\"\"
    result = conn.execute(sa.text(\"\"\"
        SELECT column_name FROM information_schema.columns
        WHERE table_name = :table AND column_name = :column
    \"\"\"), {\"table\": table_name, \"column\": column_name})
    return result.fetchone() is not None'''
new = '''def column_exists(conn, table_name, column_name):
    \"\"\"Check if a column exists in a table (PostgreSQL compatible).\"\"\"
    result = conn.execute(sa.text(
        f\"SELECT attname FROM pg_catalog.pg_attribute \"
        f\"WHERE attrelid = '{table_name}'::regclass AND attname = :column \"
        f\"AND attnum > 0 AND NOT attisdropped\"
    ), {\"column\": column_name})
    return result.fetchone() is not None'''
if old in content:
    content = content.replace(old, new)
    open(f, 'w', encoding='utf-8').write(content)
    print('  Patched 012_add_venue_config.py')
else:
    print('  012 already patched or different content, skipping')
"

    # 修复 022: 所有 information_schema 查询
    python3 -c "
import re
f = '$MIG_DIR/022_remove_country_table.py'
content = open(f, 'r', encoding='utf-8').read()
if 'information_schema' in content:
    # Replace FK check
    content = content.replace(
        '''SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_name = 'core_school'
            AND constraint_type = 'FOREIGN KEY'
            AND constraint_name = 'fk_core_school_country_id_core_country'\''',
        '''SELECT conname FROM pg_catalog.pg_constraint
            WHERE conrelid = 'core_school'::regclass
            AND contype = 'f'
            AND conname = 'fk_core_school_country_id_core_country'\'''
    )
    # Replace column check
    content = content.replace(
        '''SELECT column_name FROM information_schema.columns
            WHERE table_name = 'core_school' AND column_name = 'country_id'\''',
        '''SELECT attname FROM pg_catalog.pg_attribute
            WHERE attrelid = 'core_school'::regclass AND attname = 'country_id'
            AND attnum > 0 AND NOT attisdropped'\'''
    )
    # Replace FK lookup in other tables
    content = content.replace(
        '''SELECT tc.table_name, tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND kcu.table_name != 'core_school'
        AND kcu.column_name = 'country_id'\''',
        '''SELECT cl.relname AS table_name, con.conname AS constraint_name
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
        )\'''
    )
    # Replace column lookup in other tables
    content = content.replace(
        '''SELECT table_name FROM information_schema.columns
        WHERE column_name = 'country_id' AND table_name != 'core_school'
        AND table_schema = 'public'\''',
        '''SELECT c.relname AS table_name
        FROM pg_catalog.pg_attribute a
        JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
        JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
        WHERE a.attname = 'country_id' AND c.relname NOT IN ('core_school', 'core_country')
        AND n.nspname = 'public' AND c.relkind = 'r'
        AND a.attnum > 0 AND NOT a.attisdropped'\'''
    )
    # Replace table existence check
    content = content.replace(
        '''SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'core_country'\''',
        '''SELECT c.relname FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = 'public' AND c.relname = 'core_country'\'''
    )
    open(f, 'w', encoding='utf-8').write(content)
    print('  Patched 022_remove_country_table.py')
else:
    print('  022 already patched, skipping')
"

    # 修复 025: search_vector 列检查
    python3 -c "
f = '$MIG_DIR/025_add_fulltext_search.py'
content = open(f, 'r', encoding='utf-8').read()
old = '''SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'search_talent_document'
                    AND column_name = 'search_vector'\'''
new = '''SELECT 1 FROM pg_catalog.pg_attribute
                    WHERE attrelid = 'search_talent_document'::regclass
                    AND attname = 'search_vector'
                    AND attnum > 0 AND NOT attisdropped'\'''
if old in content:
    content = content.replace(old, new)
    open(f, 'w', encoding='utf-8').write(content)
    print('  Patched 025_add_fulltext_search.py')
else:
    print('  025 already patched, skipping')
"

    info "Migration patches applied"
else
    echo ""
    echo "Step 4: Skipped (--skip-migration-fix)"
fi

# ---- Step 5: 运行数据库迁移 ----
echo ""
echo "Step 5: Run Alembic migrations"
cd "$BACKEND_DIR"
uv run python -m alembic upgrade head && info "All migrations applied" || error "Migration failed"

# ---- Step 6: 初始化种子数据 ----
echo ""
echo "Step 6: Seed initial data"
uv run python scripts/data/init_system.py --full --force && info "Seed data initialized" || error "Seed failed"

echo ""
echo "============================================================"
echo "Database deployment complete!"
echo "============================================================"
echo ""
echo "  Admin: admin / admin123"
echo "  Demo:  demo / demo123"
echo ""
echo "  Database: $DB_NAME"
echo "  Test DB:  $DB_TEST"
echo ""
