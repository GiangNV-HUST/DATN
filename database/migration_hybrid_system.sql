-- ===================================================
-- MIGRATION: Hybrid Multi-Model System Enhancements
-- Date: 2026-01-07
-- Purpose: Add tables for session management, user preferences, and AI usage tracking
-- ===================================================

-- 1. Sessions table - CRITICAL for UC1: Authentication
-- ===================================================
CREATE TABLE IF NOT EXISTS stock.sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    user_name VARCHAR(255),
    authenticated BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    last_active TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb -- Flexible storage for additional session data
);

-- Indexes for sessions
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON stock.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON stock.sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON stock.sessions(user_id, authenticated) WHERE authenticated = TRUE;

-- Comments
COMMENT ON TABLE stock.sessions IS 'User session management for Discord bot authentication';
COMMENT ON COLUMN stock.sessions.session_id IS 'Unique session identifier';
COMMENT ON COLUMN stock.sessions.user_id IS 'Discord user ID';
COMMENT ON COLUMN stock.sessions.expires_at IS 'Session expiration timestamp';
COMMENT ON COLUMN stock.sessions.metadata IS 'Additional session data in JSON format';

-- 2. User preferences table - For personalized investment advice (UC8)
-- ===================================================
CREATE TABLE IF NOT EXISTS stock.user_preferences (
    user_id VARCHAR(255) PRIMARY KEY,
    user_name VARCHAR(255),
    risk_tolerance VARCHAR(20) CHECK (risk_tolerance IN ('low', 'medium', 'high')),
    investment_horizon VARCHAR(20) CHECK (investment_horizon IN ('short', 'medium', 'long')),
    capital DECIMAL(18,2),
    preferred_sectors TEXT[], -- Array of preferred sectors
    excluded_sectors TEXT[], -- Array of sectors to avoid
    max_single_stock_allocation DECIMAL(5,2) DEFAULT 20.00, -- Max % per stock
    enable_ai_suggestions BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indexes for user_preferences
CREATE INDEX IF NOT EXISTS idx_user_pref_risk ON stock.user_preferences(risk_tolerance);
CREATE INDEX IF NOT EXISTS idx_user_pref_updated ON stock.user_preferences(updated_at DESC);

-- Comments
COMMENT ON TABLE stock.user_preferences IS 'User investment preferences for personalized advice';
COMMENT ON COLUMN stock.user_preferences.risk_tolerance IS 'Risk tolerance level: low, medium, high';
COMMENT ON COLUMN stock.user_preferences.investment_horizon IS 'Investment timeframe: short (<1y), medium (1-3y), long (>3y)';
COMMENT ON COLUMN stock.user_preferences.capital IS 'Total capital available for investment';
COMMENT ON COLUMN stock.user_preferences.preferred_sectors IS 'Preferred industry sectors';

-- 3. AI usage logs table - Track multi-model usage and costs
-- ===================================================
CREATE TABLE IF NOT EXISTS stock.ai_usage_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    user_name VARCHAR(255),
    use_case VARCHAR(50) NOT NULL, -- UC6_analysis, UC8_investment, UC9_discovery
    agent_name VARCHAR(50), -- AnalysisSpecialist, InvestmentPlanner, DiscoverySpecialist
    model_name VARCHAR(50) NOT NULL, -- gemini_flash, gemini_pro, claude_sonnet, gpt4o
    task_description TEXT, -- Brief description of what was asked
    input_tokens INT,
    output_tokens INT,
    cost_usd DECIMAL(10,6),
    execution_time_ms INT, -- Execution time in milliseconds
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Constraints
    CONSTRAINT check_ai_use_case CHECK (
        use_case IN (
            'UC5_query', 'UC6_analysis', 'UC7_chart',
            'UC8_investment', 'UC9_discovery', 'other'
        )
    ),
    CONSTRAINT check_ai_model CHECK (
        model_name IN (
            'gemini_flash', 'gemini_pro', 'gemini_pro_vision',
            'claude_sonnet', 'claude_opus',
            'gpt4o', 'gpt4o_mini'
        )
    )
);

-- Indexes for ai_usage_logs
CREATE INDEX IF NOT EXISTS idx_ai_logs_user ON stock.ai_usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_logs_created ON stock.ai_usage_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_logs_use_case ON stock.ai_usage_logs(use_case);
CREATE INDEX IF NOT EXISTS idx_ai_logs_model ON stock.ai_usage_logs(model_name);
CREATE INDEX IF NOT EXISTS idx_ai_logs_user_case ON stock.ai_usage_logs(user_id, use_case, created_at DESC);

-- Comments
COMMENT ON TABLE stock.ai_usage_logs IS 'Track AI model usage, costs, and performance for multi-model system';
COMMENT ON COLUMN stock.ai_usage_logs.use_case IS 'Which use case triggered the AI call';
COMMENT ON COLUMN stock.ai_usage_logs.model_name IS 'AI model used: Gemini, Claude, or GPT-4o';
COMMENT ON COLUMN stock.ai_usage_logs.cost_usd IS 'Cost in USD for this API call';
COMMENT ON COLUMN stock.ai_usage_logs.execution_time_ms IS 'Time taken for the AI request';

-- 4. Investment portfolios table (OPTIONAL - for UC8 history)
-- ===================================================
CREATE TABLE IF NOT EXISTS stock.portfolios (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    user_name VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tickers TEXT[] NOT NULL, -- Array of stock tickers
    allocations DECIMAL(5,2)[] NOT NULL, -- Allocation percentages (must sum to 100)
    total_value DECIMAL(18,2),
    risk_level VARCHAR(20) CHECK (risk_level IN ('low', 'medium', 'high')),
    expected_return DECIMAL(5,2), -- Expected annual return %
    expected_volatility DECIMAL(5,2), -- Expected volatility %
    created_by_ai_model VARCHAR(50), -- Which AI model created this
    ai_reasoning TEXT, -- AI explanation for the portfolio
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indexes for portfolios
CREATE INDEX IF NOT EXISTS idx_portfolios_user ON stock.portfolios(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolios_active ON stock.portfolios(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_portfolios_created ON stock.portfolios(created_at DESC);

-- Comments
COMMENT ON TABLE stock.portfolios IS 'AI-generated investment portfolios for users';
COMMENT ON COLUMN stock.portfolios.tickers IS 'Array of stock ticker symbols';
COMMENT ON COLUMN stock.portfolios.allocations IS 'Percentage allocation for each stock (must match tickers array)';
COMMENT ON COLUMN stock.portfolios.ai_reasoning IS 'AI explanation of why this portfolio was recommended';

-- 5. Create materialized view for AI usage statistics
-- ===================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS stock.ai_usage_stats AS
SELECT
    use_case,
    model_name,
    COUNT(*) as total_calls,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(cost_usd) as total_cost,
    AVG(cost_usd) as avg_cost_per_call,
    AVG(execution_time_ms) as avg_execution_time_ms,
    SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*) * 100 as success_rate
FROM stock.ai_usage_logs
GROUP BY use_case, model_name;

-- Index for the materialized view
CREATE INDEX IF NOT EXISTS idx_ai_stats_use_case ON stock.ai_usage_stats(use_case);
CREATE INDEX IF NOT EXISTS idx_ai_stats_model ON stock.ai_usage_stats(model_name);

-- Comments
COMMENT ON MATERIALIZED VIEW stock.ai_usage_stats IS 'Aggregated statistics for AI model usage and costs';

-- 6. Function to refresh AI usage stats
-- ===================================================
CREATE OR REPLACE FUNCTION stock.refresh_ai_usage_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW stock.ai_usage_stats;
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON FUNCTION stock.refresh_ai_usage_stats() IS 'Refresh the AI usage statistics materialized view';

-- 7. Trigger to update updated_at timestamp
-- ===================================================
CREATE OR REPLACE FUNCTION stock.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to user_preferences
DROP TRIGGER IF EXISTS update_user_preferences_updated_at ON stock.user_preferences;
CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON stock.user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION stock.update_updated_at_column();

-- Apply trigger to portfolios
DROP TRIGGER IF EXISTS update_portfolios_updated_at ON stock.portfolios;
CREATE TRIGGER update_portfolios_updated_at
    BEFORE UPDATE ON stock.portfolios
    FOR EACH ROW
    EXECUTE FUNCTION stock.update_updated_at_column();

-- ===================================================
-- VERIFICATION QUERIES
-- ===================================================
-- Run these after migration to verify tables were created successfully

-- Check if all tables exist
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'stock' AND table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'stock'
    AND table_name IN ('sessions', 'user_preferences', 'ai_usage_logs', 'portfolios')
ORDER BY table_name;

-- Check indexes
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'stock'
    AND tablename IN ('sessions', 'user_preferences', 'ai_usage_logs', 'portfolios')
ORDER BY tablename, indexname;

-- ===================================================
-- SAMPLE DATA (for testing)
-- ===================================================
-- Uncomment to insert sample data for testing

/*
-- Sample session
INSERT INTO stock.sessions (session_id, user_id, user_name, expires_at)
VALUES ('session_123', '1234567890', 'TestUser', NOW() + INTERVAL '1 day');

-- Sample user preference
INSERT INTO stock.user_preferences (user_id, user_name, risk_tolerance, investment_horizon, capital)
VALUES ('1234567890', 'TestUser', 'medium', 'long', 500000000);

-- Sample AI usage log
INSERT INTO stock.ai_usage_logs (user_id, user_name, use_case, agent_name, model_name, task_description, input_tokens, output_tokens, cost_usd, execution_time_ms)
VALUES ('1234567890', 'TestUser', 'UC6_analysis', 'AnalysisSpecialist', 'claude_sonnet', 'Phân tích VCB', 1500, 800, 0.0204, 2500);
*/

-- ===================================================
-- ROLLBACK SCRIPT (if needed)
-- ===================================================
/*
DROP MATERIALIZED VIEW IF EXISTS stock.ai_usage_stats CASCADE;
DROP TABLE IF EXISTS stock.portfolios CASCADE;
DROP TABLE IF EXISTS stock.ai_usage_logs CASCADE;
DROP TABLE IF EXISTS stock.user_preferences CASCADE;
DROP TABLE IF EXISTS stock.sessions CASCADE;
DROP FUNCTION IF EXISTS stock.refresh_ai_usage_stats() CASCADE;
DROP FUNCTION IF EXISTS stock.update_updated_at_column() CASCADE;
*/
