#!/bin/bash
# ReflectAI Cron Container Entrypoint
# Configures and starts cron daemon with proper environment

set -e

echo "============================================="
echo "ReflectAI Cron Container Starting"
echo "============================================="

# Create log directories
mkdir -p /var/log/reflectai/maintenance
mkdir -p /app/logs/maintenance

# Make scripts executable
chmod +x /app/scripts/maintenance/*.sh

# Export environment variables for cron
# Cron doesn't inherit environment by default, so we write them to a file
printenv | grep -v "no_proxy" > /etc/environment

# Write environment to cron-compatible format
cat > /etc/cron.d/env.sh <<EOF
# Auto-generated environment variables for cron
export DB_HOST="${DB_HOST}"
export DB_PORT="${DB_PORT}"
export DB_NAME="${DB_NAME}"
export DB_USER="${DB_USER}"
export DB_PASSWORD="${DB_PASSWORD}"
export REDIS_HOST="${REDIS_HOST}"
export REDIS_PORT="${REDIS_PORT}"
export REDIS_PASSWORD="${REDIS_PASSWORD}"
export SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
export ENVIRONMENT="${ENVIRONMENT}"
export LOG_LEVEL="${LOG_LEVEL}"
EOF

chmod +x /etc/cron.d/env.sh

# Install crontab
echo "Installing crontab..."
crontab /app/scripts/maintenance/crontab.container

# Verify crontab installation
echo ""
echo "Installed cron jobs:"
crontab -l

# Create initial log file
echo "[$(date)] Cron container initialized" > /var/log/reflectai/cron.log

# Test database connectivity before starting cron
echo ""
echo "Testing database connectivity..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if PGPASSWORD=$DB_PASSWORD psql -h postgres -p 5432 -U $DB_USER -d $DB_NAME -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ Database connection successful"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "⏳ Waiting for database... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Database connection failed after $MAX_RETRIES attempts"
    echo "Cron will start anyway, but jobs may fail until database is available"
fi

echo ""
echo "Starting cron daemon..."
echo "============================================="

# Start cron in foreground mode
# -f = foreground (doesn't daemonize)
# -L 2 = log level 2 (log start of jobs)
exec cron -f -L 2
