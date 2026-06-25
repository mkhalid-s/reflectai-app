-- =============================================================================
-- ReflectAI PostgreSQL Initialization Script
-- =============================================================================
-- Purpose: Initialize both application and Temporal databases in single instance
-- Databases: reflectai (app), temporal (workflow orchestration)
-- =============================================================================

-- =============================================================================
-- Create Application Database User
-- =============================================================================

-- Note: The reflectai user is already created by POSTGRES_USER in docker-compose.yml
-- This script ensures it exists and has correct permissions
-- We use DO block to avoid errors if user already exists

DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = 'reflectai'
   ) THEN
      CREATE USER reflectai WITH PASSWORD 'devpassword';
   END IF;
END
$$;

-- Grant necessary privileges for application user
ALTER USER reflectai WITH CREATEDB;
ALTER USER reflectai WITH LOGIN;
GRANT ALL PRIVILEGES ON DATABASE reflectai TO reflectai;

-- =============================================================================
-- Create Temporal Database User
-- =============================================================================

-- Create temporal user for Temporal workflow engine
-- Use DO block to avoid errors if user already exists
DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = 'temporal'
   ) THEN
      CREATE USER temporal WITH PASSWORD 'temporalpassword';
   END IF;
END
$$;

-- Grant necessary privileges
ALTER USER temporal WITH CREATEDB;
ALTER USER temporal WITH LOGIN;

-- =============================================================================
-- Create Temporal Database
-- =============================================================================

-- Create temporal database owned by temporal user
CREATE DATABASE temporal
    WITH
    OWNER = temporal
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TEMPLATE = template0;

-- Grant all privileges to temporal user on temporal database
GRANT ALL PRIVILEGES ON DATABASE temporal TO temporal;

-- =============================================================================
-- Configure Temporal Database
-- =============================================================================

-- Connect to temporal database to set up permissions
\c temporal

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO temporal;
ALTER SCHEMA public OWNER TO temporal;

-- Grant default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO temporal;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO temporal;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO temporal;

-- =============================================================================
-- Verification and Logging
-- =============================================================================

-- Switch back to default database
\c reflectai

-- Log database setup
\echo '========================================='
\echo 'ReflectAI Database Initialization Complete'
\echo '========================================='
\echo ''
\echo 'Databases created:'
\echo '  1. reflectai (owner: reflectai) - Application database'
\echo '  2. temporal (owner: temporal) - Workflow orchestration database'
\echo ''
\echo 'Users created:'
\echo '  1. reflectai - Application user'
\echo '  2. temporal - Temporal workflow user'
\echo ''
\echo 'Connection strings:'
\echo '  App:      postgresql://reflectai:***@postgres:5432/reflectai'
\echo '  Temporal: postgresql://temporal:***@postgres:5432/temporal'
\echo ''
\echo '========================================='

-- List all databases for verification
\l
