-- ReflectAI Materialized View Refresh
-- Run this script periodically via cron to refresh materialized views
-- Replaces TimescaleDB's automatic continuous aggregate refresh

-- =====================================================
-- HOURLY REFRESH (Run every hour via cron)
-- =====================================================
-- Use CONCURRENTLY to avoid blocking reads during refresh
-- Note: CONCURRENTLY requires a UNIQUE index on the view

REFRESH MATERIALIZED VIEW CONCURRENTLY cost_records_hourly;

-- =====================================================
-- DAILY REFRESH (Run once per day via cron)
-- =====================================================

REFRESH MATERIALIZED VIEW CONCURRENTLY cost_records_daily;

-- =====================================================
-- MONTHLY REFRESH (Run once per day via cron)
-- =====================================================

REFRESH MATERIALIZED VIEW CONCURRENTLY cost_records_monthly;

-- =====================================================
-- ANALYZE (Update statistics after refresh)
-- =====================================================

ANALYZE cost_records_hourly;
ANALYZE cost_records_daily;
ANALYZE cost_records_monthly;

-- =====================================================
-- LOGGING
-- =====================================================

DO $$
DECLARE
    refresh_log TEXT;
BEGIN
    refresh_log := format(
        'Materialized views refreshed at %s',
        NOW()::TEXT
    );
    RAISE NOTICE '%', refresh_log;
END $$;
