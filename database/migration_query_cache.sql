-- ===================================================
-- MIGRATION: Query Cache for Performance Optimization
-- Date: 2026-01-07
-- Purpose: Add persistent cache table for expensive queries
-- Evidence: UC1, UC4, UC5, UC7 all use client-side caching in MCP Client
-- ===================================================

-- Create query_cache table for persistent caching
CREATE TABLE IF NOT EXISTS stock.query_cache (
    cache_key VARCHAR(255) PRIMARY KEY,
    query_type VARCHAR(50) NOT NULL, -- 'screening', 'price_query', 'chart_data', 'session'
    cached_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    hit_count INT DEFAULT 0,
    last_accessed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,

    CONSTRAINT check_query_type CHECK (
        query_type IN ('screening', 'price_query', 'chart_data', 'session', 'stock_data', 'other')
    )
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_query_cache_expires ON stock.query_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_query_cache_type ON stock.query_cache(query_type);
CREATE INDEX IF NOT EXISTS idx_query_cache_accessed ON stock.query_cache(last_accessed DESC);

-- Partial index for active cache only (more efficient than full index)
CREATE INDEX IF NOT EXISTS idx_query_cache_active
    ON stock.query_cache(cache_key, expires_at)
    WHERE expires_at > NOW();

-- Composite index for analytics queries
CREATE INDEX IF NOT EXISTS idx_query_cache_type_created
    ON stock.query_cache(query_type, created_at DESC);

-- Comments
COMMENT ON TABLE stock.query_cache IS 'Persistent cache for expensive database queries to improve performance across bot restarts';
COMMENT ON COLUMN stock.query_cache.cache_key IS 'Unique identifier for cached query (typically a hash of query parameters)';
COMMENT ON COLUMN stock.query_cache.query_type IS 'Type of query: screening, price_query, chart_data, session, stock_data';
COMMENT ON COLUMN stock.query_cache.cached_data IS 'Cached result stored in JSON format for flexibility';
COMMENT ON COLUMN stock.query_cache.expires_at IS 'Cache expiration timestamp (TTL)';
COMMENT ON COLUMN stock.query_cache.hit_count IS 'Number of times this cache entry was successfully used';
COMMENT ON COLUMN stock.query_cache.last_accessed IS 'Last time this cache entry was accessed';

-- ===================================================
-- UTILITY FUNCTIONS
-- ===================================================

-- Function 1: Clean expired cache entries
CREATE OR REPLACE FUNCTION stock.clean_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM stock.query_cache
    WHERE expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RAISE NOTICE 'Cleaned % expired cache entries', deleted_count;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION stock.clean_expired_cache() IS 'Remove all expired cache entries and return count of deleted rows';

-- Function 2: Get cache statistics
CREATE OR REPLACE FUNCTION stock.get_cache_stats()
RETURNS TABLE (
    query_type VARCHAR,
    total_entries BIGINT,
    active_entries BIGINT,
    total_hits BIGINT,
    avg_hits_per_entry NUMERIC,
    oldest_entry TIMESTAMPTZ,
    newest_entry TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        qc.query_type,
        COUNT(*)::BIGINT as total_entries,
        COUNT(*) FILTER (WHERE qc.expires_at > NOW())::BIGINT as active_entries,
        SUM(qc.hit_count)::BIGINT as total_hits,
        ROUND(AVG(qc.hit_count), 2) as avg_hits_per_entry,
        MIN(qc.created_at) as oldest_entry,
        MAX(qc.created_at) as newest_entry
    FROM stock.query_cache qc
    GROUP BY qc.query_type
    ORDER BY total_entries DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION stock.get_cache_stats() IS 'Get cache statistics grouped by query type';

-- Function 3: Increment hit count (atomic operation)
CREATE OR REPLACE FUNCTION stock.increment_cache_hit(p_cache_key VARCHAR)
RETURNS VOID AS $$
BEGIN
    UPDATE stock.query_cache
    SET
        hit_count = hit_count + 1,
        last_accessed = NOW()
    WHERE cache_key = p_cache_key
        AND expires_at > NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION stock.increment_cache_hit(VARCHAR) IS 'Atomically increment hit count for a cache entry';

-- ===================================================
-- CREATE MATERIALIZED VIEW FOR CACHE ANALYTICS
-- ===================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS stock.cache_performance AS
SELECT
    query_type,
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as cache_entries_created,
    SUM(hit_count) as total_hits,
    ROUND(AVG(hit_count), 2) as avg_hits_per_entry,
    ROUND(AVG(EXTRACT(EPOCH FROM (expires_at - created_at))), 0) as avg_ttl_seconds
FROM stock.query_cache
GROUP BY query_type, DATE_TRUNC('hour', created_at)
ORDER BY hour DESC, query_type;

-- Index for materialized view
CREATE INDEX IF NOT EXISTS idx_cache_perf_hour ON stock.cache_performance(hour DESC);
CREATE INDEX IF NOT EXISTS idx_cache_perf_type ON stock.cache_performance(query_type);

COMMENT ON MATERIALIZED VIEW stock.cache_performance IS 'Hourly cache performance metrics for monitoring and optimization';

-- Function to refresh cache performance stats
CREATE OR REPLACE FUNCTION stock.refresh_cache_performance()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW stock.cache_performance;
    RAISE NOTICE 'Cache performance stats refreshed';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION stock.refresh_cache_performance() IS 'Refresh the cache performance materialized view';

-- ===================================================
-- SCHEDULED MAINTENANCE (Optional - requires pg_cron extension)
-- ===================================================

-- To enable automatic cache cleanup, install pg_cron and run:
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- SELECT cron.schedule('clean-expired-cache', '*/30 * * * *', 'SELECT stock.clean_expired_cache();'); -- Every 30 minutes
-- SELECT cron.schedule('refresh-cache-stats', '0 * * * *', 'SELECT stock.refresh_cache_performance();'); -- Every hour

-- ===================================================
-- USAGE EXAMPLES
-- ===================================================

/*
-- Example 1: Insert/Update cache entry (UPSERT pattern)
INSERT INTO stock.query_cache (cache_key, query_type, cached_data, expires_at)
VALUES (
    'screening_rsi30_pe15_hash123',
    'screening',
    '{"stocks": ["VCB", "HPG", "VHM"], "count": 18, "timestamp": "2026-01-07T10:00:00Z"}'::jsonb,
    NOW() + INTERVAL '10 minutes'
)
ON CONFLICT (cache_key)
DO UPDATE SET
    cached_data = EXCLUDED.cached_data,
    expires_at = EXCLUDED.expires_at,
    hit_count = stock.query_cache.hit_count + 1,
    last_accessed = NOW();

-- Example 2: Retrieve cached data (check expiration)
SELECT cached_data, hit_count
FROM stock.query_cache
WHERE cache_key = 'screening_rsi30_pe15_hash123'
    AND expires_at > NOW();

-- Example 3: Increment hit count
SELECT stock.increment_cache_hit('screening_rsi30_pe15_hash123');

-- Example 4: Get cache statistics
SELECT * FROM stock.get_cache_stats();

-- Example 5: Clean expired cache manually
SELECT stock.clean_expired_cache();

-- Example 6: View cache performance
SELECT * FROM stock.cache_performance
WHERE query_type = 'screening'
    AND hour >= NOW() - INTERVAL '24 hours'
ORDER BY hour DESC;

-- Example 7: Find most popular cache entries
SELECT
    cache_key,
    query_type,
    hit_count,
    cached_data->>'count' as result_count,
    EXTRACT(EPOCH FROM (expires_at - created_at)) as ttl_seconds,
    last_accessed
FROM stock.query_cache
WHERE expires_at > NOW()
ORDER BY hit_count DESC
LIMIT 10;

-- Example 8: Calculate cache hit rate
WITH stats AS (
    SELECT
        COUNT(*) FILTER (WHERE hit_count > 0) as cached_queries,
        COUNT(*) as total_queries
    FROM stock.query_cache
    WHERE created_at >= NOW() - INTERVAL '1 day'
)
SELECT
    cached_queries,
    total_queries,
    ROUND(100.0 * cached_queries / NULLIF(total_queries, 0), 2) as hit_rate_percent
FROM stats;
*/

-- ===================================================
-- VERIFICATION QUERIES
-- ===================================================

-- Check if table was created successfully
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns
     WHERE table_schema = 'stock' AND table_name = 'query_cache') as column_count
FROM information_schema.tables
WHERE table_schema = 'stock' AND table_name = 'query_cache';

-- Check all indexes
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'stock' AND tablename = 'query_cache'
ORDER BY indexname;

-- Check functions
SELECT
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'stock'
    AND routine_name IN ('clean_expired_cache', 'get_cache_stats', 'increment_cache_hit', 'refresh_cache_performance')
ORDER BY routine_name;

-- Check materialized view
SELECT
    matviewname,
    (SELECT COUNT(*) FROM stock.cache_performance) as row_count
FROM pg_matviews
WHERE schemaname = 'stock' AND matviewname = 'cache_performance';

-- ===================================================
-- TEST DATA (Uncomment to insert sample cache entries)
-- ===================================================

/*
-- Sample cache for price query
INSERT INTO stock.query_cache (cache_key, query_type, cached_data, expires_at)
VALUES
    ('price_VCB_latest', 'price_query', '{"ticker": "VCB", "price": 95500, "change": 2.36}'::jsonb, NOW() + INTERVAL '1 minute'),
    ('price_HPG_latest', 'price_query', '{"ticker": "HPG", "price": 24300, "change": -0.82}'::jsonb, NOW() + INTERVAL '1 minute');

-- Sample cache for screening
INSERT INTO stock.query_cache (cache_key, query_type, cached_data, expires_at)
VALUES
    ('screening_rsi30', 'screening', '{"stocks": ["VCB", "HPG", "VHM", "TCB"], "count": 18}'::jsonb, NOW() + INTERVAL '10 minutes');

-- Sample cache for chart data
INSERT INTO stock.query_cache (cache_key, query_type, cached_data, expires_at)
VALUES
    ('chart_VCB_30d', 'chart_data', '{"ticker": "VCB", "days": 30, "data_points": 30}'::jsonb, NOW() + INTERVAL '2 minutes');

-- Verify sample data
SELECT * FROM stock.query_cache;

-- Test hit count increment
SELECT stock.increment_cache_hit('price_VCB_latest');
SELECT cache_key, hit_count FROM stock.query_cache WHERE cache_key = 'price_VCB_latest';

-- View cache stats
SELECT * FROM stock.get_cache_stats();
*/

-- ===================================================
-- ROLLBACK SCRIPT (if needed)
-- ===================================================

/*
-- Drop everything in reverse order
DROP MATERIALIZED VIEW IF EXISTS stock.cache_performance CASCADE;
DROP FUNCTION IF EXISTS stock.refresh_cache_performance() CASCADE;
DROP FUNCTION IF EXISTS stock.increment_cache_hit(VARCHAR) CASCADE;
DROP FUNCTION IF EXISTS stock.get_cache_stats() CASCADE;
DROP FUNCTION IF EXISTS stock.clean_expired_cache() CASCADE;
DROP TABLE IF EXISTS stock.query_cache CASCADE;

-- If you used pg_cron, also unschedule:
-- SELECT cron.unschedule('clean-expired-cache');
-- SELECT cron.unschedule('refresh-cache-stats');
*/

-- ===================================================
-- SUCCESS MESSAGE
-- ===================================================

DO $$
BEGIN
    RAISE NOTICE '================================================';
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE 'Created:';
    RAISE NOTICE '  - Table: stock.query_cache';
    RAISE NOTICE '  - Indexes: 5 indexes';
    RAISE NOTICE '  - Functions: 4 utility functions';
    RAISE NOTICE '  - Materialized View: stock.cache_performance';
    RAISE NOTICE '================================================';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Run verification queries above';
    RAISE NOTICE '  2. (Optional) Set up pg_cron for auto-cleanup';
    RAISE NOTICE '  3. Update MCP Client code to use persistent cache';
    RAISE NOTICE '================================================';
END $$;
