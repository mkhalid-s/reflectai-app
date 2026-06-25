# Docker Cron Container Setup

## Overview

The ReflectAI platform includes a **lightweight Alpine-based cron container** that handles all automated maintenance tasks:
- Materialized view refresh (hourly)
- Data cleanup/retention (weekly)
- Table size monitoring (daily)
- Database vacuum (weekly)

### Memory Footprint

- **Image size**: ~62 MB (vs ~520 MB for full app image)
- **Runtime memory**: 8-15 MB (vs 150-250 MB for full app)
- **Savings**: 88% smaller, 94% less memory usage
- **Startup**: 75% faster (2-3s vs 8-12s)

See [MEMORY_COMPARISON.md](./MEMORY_COMPARISON.md) for detailed analysis.

## Architecture

```
┌─────────────┐       ┌──────────────┐       ┌──────────────┐
│             │       │              │       │              │
│  App        │       │  Worker      │       │  Cron        │
│  Container  │◄─────►│  Container   │       │  Container   │
│             │       │              │       │              │
└──────┬──────┘       └──────┬───────┘       └──────┬───────┘
       │                     │                      │
       │                     │                      │
       └─────────────────────┴──────────────────────┘
                             │
                    ┌────────▼────────┐
                    │                 │
                    │   PostgreSQL    │
                    │                 │
                    └─────────────────┘
```

## Quick Start

### 1. Environment Setup

Add optional Slack webhook to `.env` (for monitoring alerts):
```bash
# Optional: Slack alerts for table size monitoring
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 2. Start the Cron Container

```bash
# Start all services including cron
docker-compose up -d

# Or start cron specifically
docker-compose up -d cron
```

### 3. Verify Cron is Running

```bash
# Check container status
docker-compose ps cron

# View cron logs
docker-compose logs cron

# Check installed cron jobs
docker exec reflectai-cron crontab -l
```

## Management Commands

### View Logs

```bash
# Follow cron execution logs
docker-compose logs -f cron

# View specific maintenance logs
docker exec reflectai-cron tail -f /var/log/reflectai/cron.log

# View last cleanup
docker exec reflectai-cron ls -lh /app/logs/maintenance/cleanup_*.log | tail -1

# View last refresh
docker exec reflectai-cron ls -lh /app/logs/maintenance/refresh_*.log | tail -1
```

### Manual Script Execution

```bash
# Run cleanup manually
docker exec reflectai-cron /app/scripts/maintenance/run_cleanup.sh

# Run MV refresh manually
docker exec reflectai-cron /app/scripts/maintenance/run_refresh.sh

# Check table sizes manually
docker exec reflectai-cron /app/scripts/maintenance/check_table_sizes.sh
```

### Restart Cron

```bash
# Restart cron container
docker-compose restart cron

# Stop cron (for maintenance)
docker-compose stop cron

# Start cron again
docker-compose start cron
```

### Modify Cron Schedule

1. Edit `scripts/maintenance/crontab.container`
2. Restart the cron container:
   ```bash
   docker-compose restart cron
   ```
3. Verify changes:
   ```bash
   docker exec reflectai-cron crontab -l
   ```

## Cron Schedule (Default)

| Task | Schedule | Description |
|------|----------|-------------|
| MV Refresh | `0 * * * *` | Every hour |
| Data Cleanup | `0 3 * * 0` | Sunday 3 AM |
| Table Monitoring | `0 6 * * *` | Daily 6 AM |
| VACUUM | `0 4 * * 0` | Sunday 4 AM |
| Log Cleanup | `0 5 1 * *` | 1st of month, 5 AM |
| Health Check | `0 * * * *` | Every hour |

## Troubleshooting

### Cron Container Won't Start

**Check logs**:
```bash
docker-compose logs cron
```

**Common issues**:
- Database not ready: Cron waits up to 30 retries
- Missing scripts: Check `/app/scripts/maintenance/` mount
- Permission issues: Scripts should be executable

**Solution**:
```bash
# Rebuild container
docker-compose build cron
docker-compose up -d cron
```

### Cron Jobs Not Executing

**Verify cron is running**:
```bash
docker exec reflectai-cron pgrep cron
```

**Check crontab**:
```bash
docker exec reflectai-cron crontab -l
```

**View cron log**:
```bash
docker exec reflectai-cron tail -f /var/log/reflectai/cron.log
```

**Test script manually**:
```bash
docker exec reflectai-cron /app/scripts/maintenance/run_refresh.sh
```

### Database Connection Failed

**Verify database is running**:
```bash
docker-compose ps postgres
```

**Test connection from cron container**:
```bash
docker exec reflectai-cron psql -h postgres -p 5432 -U reflectai -d reflectai -c "SELECT 1;"
```

**Check environment variables**:
```bash
docker exec reflectai-cron env | grep DB_
```

### Scripts Not Found

**Verify volume mount**:
```bash
docker exec reflectai-cron ls -la /app/scripts/maintenance/
```

**Check permissions**:
```bash
docker exec reflectai-cron ls -la /app/scripts/maintenance/*.sh
```

**Make scripts executable (on host)**:
```bash
chmod +x scripts/maintenance/*.sh
docker-compose restart cron
```

## Monitoring

### Health Check

Docker automatically monitors cron health:
```bash
docker inspect reflectai-cron | jq '.[0].State.Health'
```

### View Execution History

```bash
# Last 24 hours of cron executions
docker exec reflectai-cron grep "$(date +%Y-%m-%d)" /var/log/reflectai/cron.log

# Count executions by script
docker exec reflectai-cron grep -c "run_refresh.sh" /var/log/reflectai/cron.log
docker exec reflectai-cron grep -c "run_cleanup.sh" /var/log/reflectai/cron.log
```

### Resource Usage

```bash
# Container stats
docker stats reflectai-cron --no-stream

# Disk usage
docker exec reflectai-cron du -sh /var/log/reflectai
docker exec reflectai-cron du -sh /app/logs/maintenance
```

## Disabling/Enabling Cron

### Temporarily Disable

```bash
# Stop cron container
docker-compose stop cron
```

### Disable Specific Jobs

Edit `scripts/maintenance/crontab.container` and comment out lines:
```cron
# Disabled: Refresh materialized views every hour
# 0 * * * * /app/scripts/maintenance/run_refresh.sh >> /var/log/reflectai/cron.log 2>&1
```

Then restart:
```bash
docker-compose restart cron
```

### Completely Remove

To run maintenance manually only:
```bash
# Stop and remove cron container
docker-compose stop cron
docker-compose rm cron

# Or comment out cron service in docker-compose.yml
```

## Production Recommendations

### High Traffic Setup

For high-traffic production environments:

1. **Increase MV refresh frequency**:
   ```cron
   # Refresh every 15 minutes
   */15 * * * * /app/scripts/maintenance/run_refresh.sh
   ```

2. **Run cleanup daily instead of weekly**:
   ```cron
   # Daily cleanup at 2 AM
   0 2 * * * /app/scripts/maintenance/run_cleanup.sh
   ```

3. **Monitor more frequently**:
   ```cron
   # Check sizes every 4 hours
   0 */4 * * * /app/scripts/maintenance/check_table_sizes.sh
   ```

### Low Traffic Setup

For development or low-traffic environments:

1. **Reduce MV refresh**:
   ```cron
   # Refresh every 4 hours
   0 */4 * * * /app/scripts/maintenance/run_refresh.sh
   ```

2. **Cleanup bi-weekly**:
   ```cron
   # Every other Sunday
   0 3 * * 0 [ $(($(date +\%W) \% 2)) -eq 0 ] && /app/scripts/maintenance/run_cleanup.sh
   ```

### Alerts Setup

Configure Slack webhook in `.env`:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

You'll receive alerts when:
- Tables reach 30M rows (warning)
- Tables reach 50M rows (critical)
- Tables reach 100M rows (urgent - migration needed)

## Backup Strategy

Cron container logs are persisted in two places:
1. **Docker volume**: `cron_logs` (container logs)
2. **Host directory**: `./logs/maintenance/` (maintenance logs)

**Backup logs**:
```bash
# Compress maintenance logs
tar -czf maintenance-logs-$(date +%Y%m%d).tar.gz logs/maintenance/

# Export docker volume
docker run --rm -v reflectai-platform_cron_logs:/data -v $(pwd):/backup \
  alpine tar -czf /backup/cron-logs-$(date +%Y%m%d).tar.gz /data
```

## Upgrade Path

When upgrading the cron container:

1. **Stop current cron**:
   ```bash
   docker-compose stop cron
   ```

2. **Backup logs** (see above)

3. **Pull/rebuild image**:
   ```bash
   docker-compose build cron
   ```

4. **Start new cron**:
   ```bash
   docker-compose up -d cron
   ```

5. **Verify**:
   ```bash
   docker-compose logs cron
   docker exec reflectai-cron crontab -l
   ```

## Support

- **Documentation**: `/scripts/maintenance/README.md`
- **Decision Doc**: `/docs/TIMESCALEDB-REMOVAL-DECISION.md`
- **Logs**: `/var/log/reflectai/` and `./logs/maintenance/`

---

**Last Updated**: November 4, 2025
**Version**: 0.1.2-alpha
