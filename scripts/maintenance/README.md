# ReflectAI Database Maintenance Scripts

This directory contains maintenance scripts that replace TimescaleDB's automatic policies after the conversion to standard PostgreSQL.

## Overview

After removing TimescaleDB, we need manual processes for:
1. **Data Retention** - Delete old data to manage storage
2. **Materialized View Refresh** - Update aggregated cost data
3. **Table Size Monitoring** - Alert when approaching scale thresholds

## Scripts

### 1. Data Cleanup (`cleanup_old_data.sql` + `run_cleanup.sh`)

**Purpose**: Remove old data based on retention policies

**Retention Periods**:
- Activities: 90 days
- Competency History: 2 years
- Events: 30 days
- Audit Events: 7 years (legal compliance)
- Cost Records: 1 year
- User Sessions: 30 days

**Usage**:
```bash
# Run manually
./scripts/maintenance/run_cleanup.sh

# Run with custom log file
LOG_FILE=/var/log/reflectai/cleanup.log ./scripts/maintenance/run_cleanup.sh

# Run from Docker container
docker exec reflectai-app /app/scripts/maintenance/run_cleanup.sh

# Direct SQL execution
docker exec -i reflectai-postgres psql -U reflectai -d reflectai < scripts/maintenance/cleanup_old_data.sql
```

**Recommended Schedule**: Weekly (Sunday 3 AM)

**Output**: Logs row counts before/after cleanup and VACUUM statistics

### 2. Materialized View Refresh (`refresh_materialized_views.sql` + `run_refresh.sh`)

**Purpose**: Update cost aggregation materialized views

**Views Refreshed**:
- `cost_records_hourly` - Hourly LLM cost rollups
- `cost_records_daily` - Daily cost rollups
- `cost_records_monthly` - Monthly cost rollups

**Usage**:
```bash
# Run manually
./scripts/maintenance/run_refresh.sh

# Run with custom log file
LOG_FILE=/var/log/reflectai/refresh.log ./scripts/maintenance/run_refresh.sh

# Run from Docker container
docker exec reflectai-app /app/scripts/maintenance/run_refresh.sh

# Direct SQL execution
docker exec -i reflectai-postgres psql -U reflectai -d reflectai < scripts/maintenance/refresh_materialized_views.sql
```

**Recommended Schedule**: Hourly (or every 4 hours depending on usage)

**Output**: Logs view sizes before/after refresh and execution time

### 3. Table Size Monitoring (`check_table_sizes.sh`)

**Purpose**: Monitor table growth and alert when approaching TimescaleDB migration thresholds

**Thresholds**:
- 🟢 **< 30M rows**: Normal operation
- 🟡 **30M rows**: Start planning TimescaleDB evaluation
- 🟠 **50M rows**: Begin TimescaleDB migration testing
- 🔴 **100M rows**: TimescaleDB migration REQUIRED

**Usage**:
```bash
# Run manually
./scripts/maintenance/check_table_sizes.sh

# Run with Slack alerts (set webhook URL)
SLACK_WEBHOOK_URL=https://hooks.slack.com/... ./scripts/maintenance/check_table_sizes.sh

# Run from Docker container
docker exec reflectai-app /app/scripts/maintenance/check_table_sizes.sh
```

**Recommended Schedule**: Daily (6 AM)

**Output**:
- Table row counts and sizes
- Threshold analysis
- Database size summary
- Growth rate trends
- Slack alerts (if configured)

## Cron Setup

See `crontab.example` for recommended cron schedules.

**Quick Setup**:
```bash
# 1. Copy example to your project
cp scripts/maintenance/crontab.example /tmp/reflectai-cron.txt

# 2. Edit paths in the file
nano /tmp/reflectai-cron.txt

# 3. Install cron jobs
crontab /tmp/reflectai-cron.txt

# 4. Verify installation
crontab -l
```

**Recommended Production Schedule**:
```cron
# Refresh materialized views every hour
0 * * * * /path/to/scripts/maintenance/run_refresh.sh >> /var/log/reflectai/cron.log 2>&1

# Clean up old data weekly (Sunday 3 AM)
0 3 * * 0 /path/to/scripts/maintenance/run_cleanup.sh >> /var/log/reflectai/cron.log 2>&1

# Monitor table sizes daily (6 AM)
0 6 * * * /path/to/scripts/maintenance/check_table_sizes.sh >> /var/log/reflectai/cron.log 2>&1

# Vacuum database weekly (Sunday 4 AM, after cleanup)
0 4 * * 0 docker exec reflectai-postgres psql -U reflectai -d reflectai -c "VACUUM ANALYZE;" >> /var/log/reflectai/cron.log 2>&1
```

## Docker Deployment

### Option 1: Run from Host Machine

Cron jobs run on host, execute commands in Docker:
```bash
# Crontab on host
0 * * * * docker exec reflectai-app /app/scripts/maintenance/run_refresh.sh
```

**Pros**: Simple, easy to manage
**Cons**: Requires Docker on cron host

### Option 2: Run Inside Container

Add cron to the app container:
```dockerfile
# In Dockerfile
RUN apt-get update && apt-get install -y cron
COPY scripts/maintenance/crontab.container /etc/cron.d/reflectai
RUN chmod 0644 /etc/cron.d/reflectai && crontab /etc/cron.d/reflectai
```

**Pros**: Self-contained, portable
**Cons**: Container restart clears cron state

### Option 3: Separate Cron Container

Create dedicated cron service in docker-compose:
```yaml
cron:
  build: .
  command: cron -f
  volumes:
    - ./scripts:/app/scripts
  depends_on:
    - postgres
```

**Pros**: Clean separation, independent scaling
**Cons**: More complex setup

## Monitoring

### Logs

All scripts log to `logs/maintenance/`:
- `cleanup_YYYYMMDD_HHMMSS.log` - Cleanup execution logs
- `refresh_YYYYMMDD_HHMMSS.log` - MV refresh logs
- `table_sizes_YYYYMMDD.log` - Daily size monitoring
- `cron.log` - Cron execution logs

**Log Retention**: 90 days (see crontab.example for cleanup)

### Slack Alerts

Configure Slack webhook for critical alerts:
```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
./scripts/maintenance/check_table_sizes.sh
```

Alerts are sent for:
- Tables approaching 30M rows (warning)
- Tables exceeding 50M rows (critical)
- Tables exceeding 100M rows (urgent)

### Prometheus Metrics

TODO: Add Prometheus exporters for:
- `reflectai_table_rows{table="activities"}` - Current row count
- `reflectai_table_size_bytes{table="activities"}` - Table size
- `reflectai_mv_refresh_duration_seconds{view="cost_records_daily"}` - Refresh time
- `reflectai_cleanup_deleted_rows{table="activities"}` - Rows deleted

## Troubleshooting

### Script Fails with "Permission Denied"

```bash
chmod +x scripts/maintenance/*.sh
```

### Database Connection Fails

Check environment variables:
```bash
# Verify .env file exists
cat .env | grep DB_

# Test connection
docker exec reflectai-postgres psql -U reflectai -d reflectai -c "SELECT 1;"
```

### VACUUM Takes Too Long

Use `VACUUM VERBOSE` to see progress:
```sql
VACUUM VERBOSE ANALYZE activities;
```

Consider running VACUUM on specific tables during low-traffic periods.

### Materialized View Refresh Blocks Queries

Use `REFRESH MATERIALIZED VIEW CONCURRENTLY` (already in scripts).

**Requirements**:
- Materialized view must have a UNIQUE index
- Takes longer but doesn't block reads

### Disk Space Issues

Check table sizes:
```bash
./scripts/maintenance/check_table_sizes.sh
```

Run cleanup immediately:
```bash
./scripts/maintenance/run_cleanup.sh
```

## Performance Impact

### Data Cleanup
- **Duration**: ~1-5 minutes for 1M rows
- **Impact**: Locks affected rows during DELETE
- **Recommendation**: Run during off-peak hours

### MV Refresh
- **Duration**: ~10-30 seconds per view
- **Impact**: No blocking (using CONCURRENTLY)
- **Recommendation**: Can run during business hours

### Table Size Check
- **Duration**: <5 seconds
- **Impact**: Minimal (read-only queries)
- **Recommendation**: Run anytime

## Migration Path

### When to Reconsider TimescaleDB

Monitor the `check_table_sizes.sh` output:

**🟡 30M rows** (Warning):
- Start researching TimescaleDB migration
- Review compression needs
- Estimate growth trajectory
- Plan migration timeline

**🟠 50M rows** (Critical):
- Begin TimescaleDB testing
- Benchmark query performance
- Plan data migration
- Test backup/restore procedures

**🔴 100M rows** (Urgent):
- Execute TimescaleDB migration
- Use `schema.sql.timescaledb.backup` as reference
- Migrate data to hypertables
- Enable compression and retention policies

### Migration Back to TimescaleDB

See `docs/TIMESCALEDB-REMOVAL-DECISION.md` for detailed migration path.

**Quick Overview**:
1. Restore `schema.sql.timescaledb.backup`
2. Change docker image to `timescale/timescaledb:2.11.0-pg15`
3. Migrate existing data to hypertables
4. Enable policies
5. Disable these manual scripts

## Support

For issues or questions:
- Check `docs/TIMESCALEDB-REMOVAL-DECISION.md`
- Review logs in `logs/maintenance/`
- Contact DevOps team

---

**Last Updated**: November 4, 2025
**Version**: 0.1.2-alpha
**Status**: Active (Post-TimescaleDB Removal)
