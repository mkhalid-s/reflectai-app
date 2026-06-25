-- ReflectAI Data Retention Policy
-- Run this script periodically via cron to clean up old data
-- Replaces TimescaleDB's automatic retention policies

-- =====================================================
-- CONFIGURATION
-- =====================================================
-- Adjust these intervals based on your data retention requirements

-- Activities: Keep last 90 days (3 months)
DELETE FROM activities
WHERE timestamp < NOW() - INTERVAL '90 days';

-- Competency History: Keep last 2 years
DELETE FROM competency_history
WHERE timestamp < NOW() - INTERVAL '2 years';

-- Events: Keep last 30 days (system events are short-lived)
DELETE FROM events
WHERE timestamp < NOW() - INTERVAL '30 days';

-- Audit Events: Keep last 7 years (legal compliance)
DELETE FROM audit_events
WHERE timestamp < NOW() - INTERVAL '7 years';

-- Cost Records: Keep last 1 year (detail data)
DELETE FROM cost_records
WHERE timestamp < NOW() - INTERVAL '1 year';

-- User Sessions: Clean up expired sessions (older than 30 days)
DELETE FROM user_sessions
WHERE last_activity < NOW() - INTERVAL '30 days';

-- =====================================================
-- VACUUM AND ANALYZE
-- =====================================================
-- Reclaim space and update statistics after deletion

VACUUM ANALYZE activities;
VACUUM ANALYZE competency_history;
VACUUM ANALYZE events;
VACUUM ANALYZE audit_events;
VACUUM ANALYZE cost_records;
VACUUM ANALYZE user_sessions;

-- =====================================================
-- LOGGING
-- =====================================================
-- Log retention job execution
DO $$
DECLARE
    retention_log TEXT;
BEGIN
    retention_log := format(
        'Data retention completed at %s',
        NOW()::TEXT
    );
    RAISE NOTICE '%', retention_log;
END $$;
