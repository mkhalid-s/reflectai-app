#!/bin/bash
# ReflectAI Materialized View Refresh Runner
# Run this script via cron for automatic MV refresh

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
LOG_FILE="${LOG_FILE:-$PROJECT_ROOT/logs/maintenance/refresh_$(date +%Y%m%d_%H%M%S).log}"

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

echo "=============================================" | tee -a "$LOG_FILE"
echo "ReflectAI MV Refresh - $(date)" | tee -a "$LOG_FILE"
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

# Get MV sizes before refresh
echo "" | tee -a "$LOG_FILE"
echo "Materialized view status BEFORE refresh:" | tee -a "$LOG_FILE"
$PSQL_CMD -c "
SELECT
    schemaname,
    matviewname,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) AS size,
    pg_stat_get_last_vacuum_time(oid) AS last_refreshed
FROM pg_matviews
LEFT JOIN pg_class ON pg_class.relname = matviewname
WHERE schemaname = 'public'
ORDER BY matviewname;
" 2>&1 | tee -a "$LOG_FILE"

# Run refresh script
echo "" | tee -a "$LOG_FILE"
echo "Refreshing materialized views..." | tee -a "$LOG_FILE"
START_TIME=$(date +%s)

$PSQL_CMD -f "$SCRIPT_DIR/refresh_materialized_views.sql" 2>&1 | tee -a "$LOG_FILE"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Get MV sizes after refresh
echo "" | tee -a "$LOG_FILE"
echo "Materialized view status AFTER refresh:" | tee -a "$LOG_FILE"
$PSQL_CMD -c "
SELECT
    schemaname,
    matviewname,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) AS size,
    pg_stat_get_last_vacuum_time(oid) AS last_refreshed
FROM pg_matviews
LEFT JOIN pg_class ON pg_class.relname = matviewname
WHERE schemaname = 'public'
ORDER BY matviewname;
" 2>&1 | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "Refresh completed successfully in ${DURATION}s!" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "=============================================" | tee -a "$LOG_FILE"
