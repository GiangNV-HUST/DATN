-- ===================================================
-- Create compatibility layer in public schema
-- This allows MCP tools to work with both public.* and stock.* tables
-- ===================================================

-- Drop existing views/tables if any
DROP VIEW IF EXISTS public.alerts CASCADE;
DROP VIEW IF EXISTS public.subscriptions CASCADE;
DROP TABLE IF EXISTS public.alerts CASCADE;
DROP TABLE IF EXISTS public.subscriptions CASCADE;

-- Create alerts table in public schema
CREATE TABLE public.alerts (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    alert_type VARCHAR(20) NOT NULL,
    target_value NUMERIC(18,2),
    condition VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    user_name VARCHAR(255),
    CONSTRAINT check_public_alert_type CHECK (
        alert_type IN ('price', 'avg_volume_5', 'avg_volume_10', 'avg_volume_20',
                      'ma5', 'ma10', 'ma20', 'ma50', 'ma100',
                      'bb_upper', 'bb_middle', 'bb_lower',
                      'rsi', 'macd_diff', 'macd_main', 'macd_signal')
    ),
    CONSTRAINT check_public_condition CHECK (
        condition IN ('above', 'below', 'cross_above', 'cross_below',
                     'above_70', 'neg_to_pos', 'pos_to_neg')
    )
);

-- Create subscriptions table in public schema
CREATE TABLE public.subscriptions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_name VARCHAR(255) NOT NULL,
    CONSTRAINT subscriptions_user_id_symbol_key UNIQUE (user_id, symbol)
);

-- Create indexes
CREATE INDEX idx_public_alerts_symbol ON public.alerts(symbol);
CREATE INDEX idx_public_alerts_user_id ON public.alerts(user_id);
CREATE INDEX idx_public_alerts_active ON public.alerts(is_active);

CREATE INDEX idx_public_subscriptions_symbol ON public.subscriptions(symbol);
CREATE INDEX idx_public_subscriptions_user_id ON public.subscriptions(user_id);

-- Create trigger functions to sync data from public to stock schema
CREATE OR REPLACE FUNCTION sync_alert_to_stock()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO stock.alert (user_id, ticker, type, price_value, condition, user_name)
        VALUES (NEW.user_id, NEW.symbol, NEW.alert_type, NEW.target_value, NEW.condition, NEW.user_name)
        ON CONFLICT (id) DO NOTHING;
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        UPDATE stock.alert
        SET user_id = NEW.user_id,
            ticker = NEW.symbol,
            type = NEW.alert_type,
            price_value = NEW.target_value,
            condition = NEW.condition,
            user_name = NEW.user_name
        WHERE id = NEW.id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        DELETE FROM stock.alert WHERE id = OLD.id;
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION sync_subscription_to_stock()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO stock.subscribe (user_id, ticker, user_name)
        VALUES (NEW.user_id, NEW.symbol, NEW.user_name)
        ON CONFLICT (user_id, ticker) DO NOTHING;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        DELETE FROM stock.subscribe WHERE user_id = OLD.user_id AND ticker = OLD.symbol;
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create triggers
CREATE TRIGGER trigger_sync_alert_to_stock
AFTER INSERT OR UPDATE OR DELETE ON public.alerts
FOR EACH ROW EXECUTE FUNCTION sync_alert_to_stock();

CREATE TRIGGER trigger_sync_subscription_to_stock
AFTER INSERT OR DELETE ON public.subscriptions
FOR EACH ROW EXECUTE FUNCTION sync_subscription_to_stock();

-- Sync existing data from stock to public (if any)
INSERT INTO public.alerts (user_id, symbol, alert_type, target_value, condition, created_at, user_name)
SELECT user_id, ticker, type, price_value, condition, create_at, user_name
FROM stock.alert
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.subscriptions (user_id, symbol, created_at, user_name)
SELECT user_id, ticker, create_at, user_name
FROM stock.subscribe
ON CONFLICT (user_id, symbol) DO NOTHING;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON public.alerts TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.subscriptions TO postgres;
GRANT USAGE, SELECT ON SEQUENCE public.alerts_id_seq TO postgres;
GRANT USAGE, SELECT ON SEQUENCE public.subscriptions_id_seq TO postgres;

COMMENT ON TABLE public.alerts IS 'Compatibility layer for MCP tools - syncs to stock.alert';
COMMENT ON TABLE public.subscriptions IS 'Compatibility layer for MCP tools - syncs to stock.subscribe';
