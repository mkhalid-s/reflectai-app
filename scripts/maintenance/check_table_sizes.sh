#!/bin/bash
# ReflectAI Table Size Monitor
# Check table sizes and alert if approaching TimescaleDB migration thresholds
#
# Thresholds:
# - 30M rows: Start planning TimescaleDB evaluation
# - 50M rows: Begin TimescaleDB migration testing
# - 100M rows: TimescaleDB migration should be completed

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
LOG_FILE="${LOG_FILE:-$PROJECT_ROOT/logs/maintenance/table_sizes_$(date +%Y%m%d).log}"

# Alert thresholds (row counts)
THRESHOLD_WARNING=30000000   # 30M rows - Yellow alert
THRESHOLD_CRITICAL=50000000  # 50M rows - Red alert
THRESHOLD_URGENT=100000000   # 100M rows - Urgent migration needed

# Slack webhook for alerts (optional)
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

echo "=============================================" | tee -a "$LOG_FILE"
echo "ReflectAI Table Size Check - $(date)" | tee -a "$LOG_FILE"
echo "=============================================" | tee -a "$LOG_FILE"

# Check if running in Docker or local
if [ -f /.dockerenv ] || [ -n "$DOCKER_CONTAINER" ]; then
    PSQL_CMD="psql -U $DB_USER -d $DB_NAME"
else
    if command -v docker &> /dev/null && docker ps | grep -q reflectai-postgres; then
        PSQL_CMD="docker exec -i reflectai-postgres psql -U $DB_USER -d $DB_NAME"
    else
        PSQL_CMD="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"
    fi
fi

# Function to send Slack alert
send_slack_alert() {
    local level=$1
    local table=$2
    local rows=$3
    local message=$4

    if [ -n "$SLACK_WEBHOOK" ]; then
        local color="danger"
        if [ "$level" = "warning" ]; then
            color="warning"
        fi

        curl -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"title\": \"⚠️ ReflectAI Database Alert\",
                    \"text\": \"$message\",
                    \"fields\": [
                        {\"title\": \"Table\", \"value\": \"$table\", \"short\": true},
                        {\"title\": \"Row Count\", \"value\": \"$(printf "%'d" $rows)\", \"short\": true}
                    ],
                    \"footer\": \"ReflectAI Monitoring\",
                    \"ts\": $(date +%s)
                }]
            }" 2>&1 | tee -a "$LOG_FILE"
    fi
}

# Get table sizes and row counts
echo "" | tee -a "$LOG_FILE"
echo "Table Statistics:" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

TABLE_STATS=$($PSQL_CMD -t -c "
SELECT
    schemaname || '.' || tablename AS table_name,
    n_live_tup AS row_count,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_stat_user_tables
WHERE schemaname = 'public'
    AND tablename IN ('activities', 'competency_history', 'events', 'audit_events', 'cost_records')
ORDER BY n_live_tup DESC;
" 2>&1)

echo "$TABLE_STATS" | column -t | tee -a "$LOG_FILE"

# Check critical tables against thresholds
echo "" | tee -a "$LOG_FILE"
echo "Threshold Analysis:" | tee -a "$LOG_FILE"
echo "  Warning: $(printf "%'d" $THRESHOLD_WARNING) rows (30M)" | tee -a "$LOG_FILE"
echo "  Critical: $(printf "%'d" $THRESHOLD_CRITICAL) rows (50M)" | tee -a "$LOG_FILE"
echo "  Urgent: $(printf "%'d" $THRESHOLD_URGENT) rows (100M)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

ALERTS_TRIGGERED=0

# Check each critical table
for table in activities competency_history events audit_events cost_records; do
    ROW_COUNT=$($PSQL_CMD -t -c "SELECT n_live_tup FROM pg_stat_user_tables WHERE tablename = '$table';" | tr -d ' ')

    if [ -z "$ROW_COUNT" ]; then
        ROW_COUNT=0
    fi

    if [ "$ROW_COUNT" -ge "$THRESHOLD_URGENT" ]; then
        MESSAGE="🔴 URGENT: Table '$table' has $(printf "%'d" $ROW_COUNT) rows! TimescaleDB migration REQUIRED NOW!"
        echo "$MESSAGE" | tee -a "$LOG_FILE"
        send_slack_alert "critical" "$table" "$ROW_COUNT" "$MESSAGE"
        ALERTS_TRIGGERED=$((ALERTS_TRIGGERED + 1))
    elif [ "$ROW_COUNT" -ge "$THRESHOLD_CRITICAL" ]; then
        MESSAGE="🟠 CRITICAL: Table '$table' has $(printf "%'d" $ROW_COUNT) rows. Begin TimescaleDB migration testing!"
        echo "$MESSAGE" | tee -a "$LOG_FILE"
        send_slack_alert "critical" "$table" "$ROW_COUNT" "$MESSAGE"
        ALERTS_TRIGGERED=$((ALERTS_TRIGGERED + 1))
    elif [ "$ROW_COUNT" -ge "$THRESHOLD_WARNING" ]; then
        MESSAGE="🟡 WARNING: Table '$table' has $(printf "%'d" $ROW_COUNT) rows. Start planning TimescaleDB evaluation."
        echo "$MESSAGE" | tee -a "$LOG_FILE"
        send_slack_alert "warning" "$table" "$ROW_COUNT" "$MESSAGE"
        ALERTS_TRIGGERED=$((ALERTS_TRIGGERED + 1))
    else
        PERCENTAGE=$((ROW_COUNT * 100 / THRESHOLD_WARNING))
        echo "✅ OK: Table '$table' has $(printf "%'d" $ROW_COUNT) rows ($PERCENTAGE% of warning threshold)" | tee -a "$LOG_FILE"
    fi
done

# Database size summary
echo "" | tee -a "$LOG_FILE"
echo "Database Size Summary:" | tee -a "$LOG_FILE"
$PSQL_CMD -c "
SELECT
    pg_database.datname,
    pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
WHERE datname = '$DB_NAME';
" 2>&1 | tee -a "$LOG_FILE"

# Growth rate analysis (if we have previous logs)
echo "" | tee -a "$LOG_FILE"
echo "Growth Rate Analysis:" | tee -a "$LOG_FILE"

YESTERDAY_LOG="$PROJECT_ROOT/logs/maintenance/table_sizes_$(date -v-1d +%Y%m%d 2>/dev/null || date -d '1 day ago' +%Y%m%d 2>/dev/null || echo 'unknown').log"
if [ -f "$YESTERDAY_LOG" ]; then
    echo "  Comparing with yesterday's data..." | tee -a "$LOG_FILE"
    # Simple comparison logic here
    echo "  (Growth rate tracking - TODO: implement delta calculation)" | tee -a "$LOG_FILE"
else
    echo "  No previous data for comparison" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
if [ "$ALERTS_TRIGGERED" -eq 0 ]; then
    echo "✅ All tables within normal thresholds" | tee -a "$LOG_FILE"
else
    echo "⚠️ $ALERTS_TRIGGERED alert(s) triggered - review required!" | tee -a "$LOG_FILE"
fi

echo "=============================================" | tee -a "$LOG_FILE"

# Exit with error code if critical alerts triggered
if [ "$ALERTS_TRIGGERED" -gt 0 ]; then
    exit 1
else
    exit 0
fi
