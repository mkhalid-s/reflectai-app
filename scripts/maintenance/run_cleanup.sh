#!/bin/bash
# ReflectAI Data Cleanup Runner
# Run this script via cron for automatic data retention

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Load environment variables if .env exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-reflectai}"
DB_USER="${DB_USER:-reflectai}"
LOG_FILE="${LOG_FILE:-$PROJECT_ROOT/logs/maintenance/cleanup_$(date +%Y%m%d_%H%M%S).log}"

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

echo "=============================================" | tee -a "$LOG_FILE"
echo "ReflectAI Data Cleanup - $(date)" | tee -a "$LOG_FILE"
echo "=============================================" | tee -a "$LOG_FILE"

# Check if running in Docker or local
if [ -f /.dockerenv ] || [ -n "$DOCKER_CONTAINER" ]; then
    echo "Running inside Docker container" | tee -a "$LOG_FILE"
    PSQL_CMD="psql -U $DB_USER -d $DB_NAME"
else
    echo "Running on host machine" | tee -a "$LOG_FILE"
    if command -v docker &> /dev/null && docker ps | grep -q reflectai-postgres; then
        echo "Using Docker container for database" | tee -a "$LOG_FILE"
        PSQL_CMD="docker exec -i reflectai-postgres psql -U $DB_USER -d $DB_NAME"
    else
        echo "Using local PostgreSQL" | tee -a "$LOG_FILE"
        PSQL_CMD="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"
    fi
fi

# Get row counts before cleanup
echo "" | tee -a "$LOG_FILE"
echo "Row counts BEFORE cleanup:" | tee -a "$LOG_FILE"
$PSQL_CMD -c "
SELECT
    'activities' AS table_name,
    COUNT(*) AS rows
FROM activities
UNION ALL
SELECT 'competency_history', COUNT(*) FROM competency_history
UNION ALL
SELECT 'events', COUNT(*) FROM events
UNION ALL
SELECT 'audit_events', COUNT(*) FROM audit_events
UNION ALL
SELECT 'cost_records', COUNT(*) FROM cost_records
UNION ALL
SELECT 'user_sessions', COUNT(*) FROM user_sessions
ORDER BY table_name;
" 2>&1 | tee -a "$LOG_FILE"

# Run cleanup script
echo "" | tee -a "$LOG_FILE"
echo "Running data cleanup..." | tee -a "$LOG_FILE"
$PSQL_CMD -f "$SCRIPT_DIR/cleanup_old_data.sql" 2>&1 | tee -a "$LOG_FILE"

# Get row counts after cleanup
echo "" | tee -a "$LOG_FILE"
echo "Row counts AFTER cleanup:" | tee -a "$LOG_FILE"
$PSQL_CMD -c "
SELECT
    'activities' AS table_name,
    COUNT(*) AS rows
FROM activities
UNION ALL
SELECT 'competency_history', COUNT(*) FROM competency_history
UNION ALL
SELECT 'events', COUNT(*) FROM events
UNION ALL
SELECT 'audit_events', COUNT(*) FROM audit_events
UNION ALL
SELECT 'cost_records', COUNT(*) FROM cost_records
UNION ALL
SELECT 'user_sessions', COUNT(*) FROM user_sessions
ORDER BY table_name;
" 2>&1 | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "Cleanup completed successfully!" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "=============================================" | tee -a "$LOG_FILE"
