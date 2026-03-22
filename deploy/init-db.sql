-- Initial database setup
-- This script is run when the PostgreSQL container is first created

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE talent_db TO talent_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO talent_user;
