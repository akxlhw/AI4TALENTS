-- 智能人才库 - 数据库初始化脚本
-- 可在PostgreSQL中手动执行

-- 启用扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================
-- 国家表
-- ============================================
CREATE TABLE IF NOT EXISTS core_country (
    country_id SERIAL PRIMARY KEY,
    country_code VARCHAR(10) UNIQUE NOT NULL,
    country_name_cn VARCHAR(100) NOT NULL,
    country_name_en VARCHAR(100),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_core_country_country_code ON core_country(country_code);

-- ============================================
-- 学校表
-- ============================================
CREATE TABLE IF NOT EXISTS core_school (
    school_id SERIAL PRIMARY KEY,
    school_name VARCHAR(255) NOT NULL,
    school_alias VARCHAR(255),
    country_id INTEGER NOT NULL REFERENCES core_country(country_id),
    school_intro TEXT,
    homepage_url VARCHAR(500),
    professor_count INTEGER DEFAULT 0,
    student_count INTEGER DEFAULT 0,
    is_visible BOOLEAN DEFAULT TRUE NOT NULL,
    status VARCHAR(20) DEFAULT 'active' NOT NULL,
    source_type VARCHAR(50),
    source_record_id VARCHAR(100),
    last_sync_batch_id INTEGER,
    department_name VARCHAR(255),
    lab_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_core_school_school_name ON core_school(school_name);
CREATE INDEX IF NOT EXISTS ix_core_school_country_id ON core_school(country_id);
CREATE INDEX IF NOT EXISTS ix_core_school_status_visible ON core_school(status, is_visible);

-- ============================================
-- 学校别名表
-- ============================================
CREATE TABLE IF NOT EXISTS core_school_alias (
    alias_id SERIAL PRIMARY KEY,
    school_id INTEGER NOT NULL REFERENCES core_school(school_id),
    alias_name VARCHAR(255) NOT NULL,
    alias_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_core_school_alias_school_id ON core_school_alias(school_id);
CREATE INDEX IF NOT EXISTS ix_core_school_alias_alias_name ON core_school_alias(alias_name);

-- ============================================
-- 人才表
-- ============================================
CREATE TABLE IF NOT EXISTS core_talent (
    talent_id SERIAL PRIMARY KEY,
    source_type VARCHAR(50),
    source_record_id VARCHAR(100),
    last_sync_batch_id INTEGER,
    name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    orcid VARCHAR(50),
    school_id INTEGER REFERENCES core_school(school_id),
    current_title VARCHAR(255),
    role_type VARCHAR(20) DEFAULT 'unknown' NOT NULL,
    role_confidence FLOAT DEFAULT 0.0,
    topic_tags TEXT[],
    research_interests TEXT,
    summary TEXT,
    works_count INTEGER DEFAULT 0,
    cited_by_count INTEGER DEFAULT 0,
    h_index INTEGER DEFAULT 0,
    latest_active_year INTEGER,
    visibility_status VARCHAR(20) DEFAULT 'active' NOT NULL,
    is_visible BOOLEAN DEFAULT TRUE NOT NULL,
    unified_person_id VARCHAR(100),
    department_name VARCHAR(255),
    lab_name VARCHAR(255),
    extra_data JSONB,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_core_talent_name ON core_talent(name);
CREATE INDEX IF NOT EXISTS ix_core_talent_school_id ON core_talent(school_id);
CREATE INDEX IF NOT EXISTS ix_core_talent_role_type ON core_talent(role_type);
CREATE INDEX IF NOT EXISTS ix_core_talent_school_role ON core_talent(school_id, role_type, is_visible);

-- ============================================
-- 角色档案表
-- ============================================
CREATE TABLE IF NOT EXISTS core_role_profile (
    profile_id SERIAL PRIMARY KEY,
    talent_id INTEGER UNIQUE NOT NULL REFERENCES core_talent(talent_id),
    role_type VARCHAR(20) DEFAULT 'unknown' NOT NULL,
    role_confidence FLOAT DEFAULT 0.0,
    role_reason TEXT,
    identification_method VARCHAR(50),
    identified_at VARCHAR(50),
    position_title VARCHAR(255),
    academic_age INTEGER,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- ============================================
-- 代表成果表
-- ============================================
CREATE TABLE IF NOT EXISTS core_selected_work (
    work_id SERIAL PRIMARY KEY,
    talent_id INTEGER NOT NULL REFERENCES core_talent(talent_id),
    title VARCHAR(500) NOT NULL,
    publication_year INTEGER,
    venue_name VARCHAR(255),
    citation_count INTEGER DEFAULT 0,
    source_work_id VARCHAR(100),
    doi VARCHAR(100),
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_core_selected_work_talent_id ON core_selected_work(talent_id);

-- ============================================
-- 总览统计快照表
-- ============================================
CREATE TABLE IF NOT EXISTS stat_overview_snapshot (
    snapshot_id SERIAL PRIMARY KEY,
    stat_version VARCHAR(50) NOT NULL,
    generated_at VARCHAR(50) NOT NULL,
    school_count INTEGER DEFAULT 0,
    professor_count INTEGER DEFAULT 0,
    student_count INTEGER DEFAULT 0,
    talent_count INTEGER DEFAULT 0,
    generated_by_batch_id INTEGER,
    is_active INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS ix_stat_overview_version ON stat_overview_snapshot(stat_version);

-- ============================================
-- 学校统计快照表
-- ============================================
CREATE TABLE IF NOT EXISTS stat_school_snapshot (
    snapshot_id SERIAL PRIMARY KEY,
    school_id INTEGER NOT NULL REFERENCES core_school(school_id),
    stat_version VARCHAR(50) NOT NULL,
    generated_at VARCHAR(50) NOT NULL,
    professor_count INTEGER DEFAULT 0,
    student_count INTEGER DEFAULT 0,
    talent_count INTEGER DEFAULT 0,
    graduate_count INTEGER DEFAULT 0,
    unknown_count INTEGER DEFAULT 0,
    generated_by_batch_id INTEGER,
    is_active INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS ix_stat_school_snapshot_school_id ON stat_school_snapshot(school_id);

-- ============================================
-- 用户账号表
-- ============================================
CREATE TABLE IF NOT EXISTS iam_user_account (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_type VARCHAR(20) DEFAULT 'user' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    status VARCHAR(20) DEFAULT 'active' NOT NULL,
    display_name VARCHAR(100),
    department VARCHAR(255),
    last_login_at TIMESTAMP,
    last_login_ip VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_iam_user_username ON iam_user_account(username);

-- ============================================
-- 用户学校权限表
-- ============================================
CREATE TABLE IF NOT EXISTS iam_user_school_scope (
    scope_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES iam_user_account(user_id),
    scope_type VARCHAR(20) NOT NULL,
    scope_value VARCHAR(100),
    granted_by INTEGER NOT NULL,
    granted_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
    UNIQUE (user_id, scope_type, scope_value)
);

CREATE INDEX IF NOT EXISTS ix_iam_scope_user_id ON iam_user_school_scope(user_id);

-- ============================================
-- 同步批次表
-- ============================================
CREATE TABLE IF NOT EXISTS sync_batch (
    batch_id SERIAL PRIMARY KEY,
    batch_code VARCHAR(50) UNIQUE NOT NULL,
    batch_type VARCHAR(20) NOT NULL,
    source_type VARCHAR(50) DEFAULT 'openalex',
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    total_records INTEGER DEFAULT 0,
    success_records INTEGER DEFAULT 0,
    failed_records INTEGER DEFAULT 0,
    error_message TEXT,
    error_details JSONB,
    created_by VARCHAR(50) DEFAULT 'system',
    config_snapshot JSONB
);

CREATE INDEX IF NOT EXISTS ix_sync_batch_code ON sync_batch(batch_code);
CREATE INDEX IF NOT EXISTS ix_sync_batch_status ON sync_batch(status);

-- ============================================
-- 原始数据记录表
-- ============================================
CREATE TABLE IF NOT EXISTS raw_source_record (
    record_id SERIAL PRIMARY KEY,
    batch_id INTEGER NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(100) NOT NULL,
    raw_data JSONB NOT NULL,
    processed_status VARCHAR(20) DEFAULT 'pending',
    processed_at TIMESTAMP,
    error_info TEXT,
    fetched_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_raw_record_batch_id ON raw_source_record(batch_id);
CREATE INDEX IF NOT EXISTS ix_raw_record_source ON raw_source_record(source_type, source_id);

-- ============================================
-- 搜索投影表
-- ============================================
CREATE TABLE IF NOT EXISTS search_talent_document (
    document_id SERIAL PRIMARY KEY,
    talent_id INTEGER UNIQUE NOT NULL,
    school_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    school_name VARCHAR(255),
    country_code VARCHAR(10),
    search_text TEXT NOT NULL,
    role_type VARCHAR(20) NOT NULL,
    topic_tags TEXT[],
    works_count INTEGER DEFAULT 0,
    cited_by_count INTEGER DEFAULT 0,
    h_index INTEGER DEFAULT 0,
    latest_active_year INTEGER,
    orcid VARCHAR(50),
    batch_id INTEGER,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
    extra_data JSONB
);

CREATE INDEX IF NOT EXISTS ix_search_talent_id ON search_talent_document(talent_id);
CREATE INDEX IF NOT EXISTS ix_search_school_id ON search_talent_document(school_id);
CREATE INDEX IF NOT EXISTS ix_search_role_type ON search_talent_document(role_type);
CREATE INDEX IF NOT EXISTS ix_search_text ON search_talent_document USING gin(to_tsvector('simple', search_text));

-- ============================================
-- 审计日志表
-- ============================================
CREATE TABLE IF NOT EXISTS audit_operation_log (
    log_id SERIAL PRIMARY KEY,
    event_time TIMESTAMP NOT NULL,
    user_id INTEGER,
    user_ip VARCHAR(50),
    event_type VARCHAR(50) NOT NULL,
    event_subtype VARCHAR(50),
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    operation VARCHAR(50) NOT NULL,
    operation_detail JSONB,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    request_id VARCHAR(100),
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS ix_audit_event_time ON audit_operation_log(event_time);
CREATE INDEX IF NOT EXISTS ix_audit_user_event ON audit_operation_log(user_id, event_time);
CREATE INDEX IF NOT EXISTS ix_audit_event_type ON audit_operation_log(event_type, event_time);

-- ============================================
-- 触发器：自动更新 updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为每个表创建触发器
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN SELECT table_name FROM information_schema.tables
             WHERE table_schema = 'public' AND table_name LIKE 'core_%' OR table_name LIKE 'iam_%' OR table_name LIKE 'stat_%'
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS update_%s_updated_at ON %s', t, t);
        EXECUTE format('CREATE TRIGGER update_%s_updated_at BEFORE UPDATE ON %s FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()', t, t);
    END LOOP;
END;
$$;

-- ============================================
-- Raw data layer indexes (added in migration 020)
-- ============================================
CREATE INDEX IF NOT EXISTS ix_raw_work_fetch_task_id ON raw_work(fetch_task_id);
CREATE INDEX IF NOT EXISTS ix_raw_work_sub_task_id ON raw_work(sub_task_id);
CREATE INDEX IF NOT EXISTS ix_raw_author_fetch_task_id ON raw_author(fetch_task_id);
CREATE INDEX IF NOT EXISTS ix_rel_author_tech_belong_source_venue_id ON rel_author_tech_belong(source_venue_id);
CREATE INDEX IF NOT EXISTS ix_rel_author_tech_belong_source_task_id ON rel_author_tech_belong(source_task_id);
