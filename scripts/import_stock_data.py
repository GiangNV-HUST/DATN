"""
Script import dữ liệu stock vào PostgreSQL database
Sử dụng vnstock để lấy dữ liệu và lưu vào database cho screener
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta

import psycopg2
import pandas as pd
from vnstock import Vnstock

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database config
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5434'),
    'database': os.getenv('DB_NAME', 'stock'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres123')
}

# Top stocks to import
TOP_STOCKS = [
    # Banks
    'VCB', 'TCB', 'CTG', 'MBB', 'VPB', 'BID', 'ACB', 'STB', 'HDB', 'TPB',
    # Technology
    'FPT', 'CMG', 'ELC',
    # Real Estate
    'VIC', 'VHM', 'VRE', 'NVL', 'KDH', 'DXG',
    # Steel & Materials
    'HPG', 'HSG', 'NKG', 'SMC',
    # Consumer
    'VNM', 'MSN', 'SAB', 'MWG', 'PNJ',
    # Energy
    'GAS', 'PLX', 'PVD', 'PVS', 'POW',
    # Securities
    'SSI', 'VCI', 'HCM', 'VND', 'SHS',
    # Others
    'REE', 'DGC', 'GVR', 'DHG', 'DPM'
]


def create_tables(conn):
    """Create necessary tables if not exist"""
    cur = conn.cursor()

    # Table for stock screening data
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_screener (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(20) NOT NULL,
            exchange VARCHAR(20),
            industry VARCHAR(100),

            -- Price data
            close NUMERIC,
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            volume BIGINT,
            change_percent_1d NUMERIC,

            -- Fundamental metrics
            market_cap NUMERIC,
            pe NUMERIC,
            pb NUMERIC,
            roe NUMERIC,
            eps NUMERIC,
            dividend_yield NUMERIC,

            -- Technical indicators
            rsi14 NUMERIC,
            ma5 NUMERIC,
            ma10 NUMERIC,
            ma20 NUMERIC,
            ma50 NUMERIC,

            -- Trading metrics
            avg_trading_value_20d NUMERIC,
            foreign_buy_value NUMERIC,

            -- Metadata
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(ticker)
        )
    """)

    # Table for historical price data
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_1d (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(20) NOT NULL,
            time TIMESTAMP NOT NULL,
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            volume BIGINT,

            UNIQUE(ticker, time)
        )
    """)

    conn.commit()
    logger.info("Tables created successfully")


def fetch_stock_data(symbol: str) -> dict:
    """Fetch stock data from vnstock with rate limiting"""
    try:
        time.sleep(2)  # Rate limiting

        stock = Vnstock().stock(symbol=symbol, source='VCI')

        # Get price history (30 days)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')

        history = stock.quote.history(start=start_date, end=end_date)

        if history.empty:
            logger.warning(f"No price data for {symbol}")
            return None

        # Calculate technical indicators
        df = history.copy()
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma50'] = df['close'].rolling(window=50).mean()

        # RSI calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi14'] = 100 - (100 / (1 + rs))

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        # Calculate change percent
        change_pct = ((latest['close'] - prev['close']) / prev['close'] * 100) if prev['close'] > 0 else 0

        # Get company overview for fundamentals
        time.sleep(2)  # Rate limiting
        try:
            overview = stock.company.overview()
            overview_data = overview.to_dict(orient='records')[0] if not overview.empty else {}
        except:
            overview_data = {}

        # Get financial ratios
        time.sleep(2)  # Rate limiting
        try:
            ratios = stock.finance.ratio(period='quarter')
            ratio_data = ratios.to_dict(orient='records')[0] if not ratios.empty else {}
        except:
            ratio_data = {}

        # Build result
        result = {
            'ticker': symbol,
            'exchange': overview_data.get('exchange', 'HOSE'),
            'industry': overview_data.get('industry', ''),
            'close': float(latest['close']),
            'open': float(latest['open']),
            'high': float(latest['high']),
            'low': float(latest['low']),
            'volume': int(latest['volume']),
            'change_percent_1d': float(change_pct),
            'market_cap': overview_data.get('market_cap'),
            'pe': ratio_data.get('pe') or overview_data.get('pe'),
            'pb': ratio_data.get('pb') or overview_data.get('pb'),
            'roe': ratio_data.get('roe'),
            'eps': ratio_data.get('eps'),
            'dividend_yield': ratio_data.get('dividend_yield'),
            'rsi14': float(latest['rsi14']) if pd.notna(latest['rsi14']) else None,
            'ma5': float(latest['ma5']) if pd.notna(latest['ma5']) else None,
            'ma10': float(latest['ma10']) if pd.notna(latest['ma10']) else None,
            'ma20': float(latest['ma20']) if pd.notna(latest['ma20']) else None,
            'ma50': float(latest['ma50']) if pd.notna(latest['ma50']) else None,
            'avg_trading_value_20d': float(df['volume'].tail(20).mean() * df['close'].tail(20).mean()) if len(df) >= 20 else None,
            'history': df.to_dict(orient='records')
        }

        return result

    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None


def save_to_database(conn, data: dict):
    """Save stock data to database"""
    if not data:
        return

    cur = conn.cursor()

    try:
        # Upsert screener data
        cur.execute("""
            INSERT INTO stock_screener (
                ticker, exchange, industry, close, open, high, low, volume,
                change_percent_1d, market_cap, pe, pb, roe, eps, dividend_yield,
                rsi14, ma5, ma10, ma20, ma50, avg_trading_value_20d, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
            )
            ON CONFLICT (ticker) DO UPDATE SET
                exchange = EXCLUDED.exchange,
                industry = EXCLUDED.industry,
                close = EXCLUDED.close,
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                volume = EXCLUDED.volume,
                change_percent_1d = EXCLUDED.change_percent_1d,
                market_cap = EXCLUDED.market_cap,
                pe = EXCLUDED.pe,
                pb = EXCLUDED.pb,
                roe = EXCLUDED.roe,
                eps = EXCLUDED.eps,
                dividend_yield = EXCLUDED.dividend_yield,
                rsi14 = EXCLUDED.rsi14,
                ma5 = EXCLUDED.ma5,
                ma10 = EXCLUDED.ma10,
                ma20 = EXCLUDED.ma20,
                ma50 = EXCLUDED.ma50,
                avg_trading_value_20d = EXCLUDED.avg_trading_value_20d,
                updated_at = CURRENT_TIMESTAMP
        """, (
            data['ticker'], data['exchange'], data['industry'],
            data['close'], data['open'], data['high'], data['low'], data['volume'],
            data['change_percent_1d'], data['market_cap'], data['pe'], data['pb'],
            data['roe'], data['eps'], data['dividend_yield'],
            data['rsi14'], data['ma5'], data['ma10'], data['ma20'], data['ma50'],
            data['avg_trading_value_20d']
        ))

        # Insert historical data
        for row in data.get('history', []):
            try:
                cur.execute("""
                    INSERT INTO stock_1d (ticker, time, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticker, time) DO NOTHING
                """, (
                    data['ticker'],
                    row['time'],
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume']
                ))
            except Exception as e:
                pass  # Skip duplicates

        conn.commit()
        logger.info(f"Saved data for {data['ticker']}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving {data['ticker']}: {e}")


def main():
    """Main function to import stock data"""
    logger.info("Starting stock data import...")
    logger.info(f"Will import {len(TOP_STOCKS)} stocks")

    # Connect to database
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Connected to database")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return

    # Create tables
    create_tables(conn)

    # Import each stock
    success_count = 0
    for i, symbol in enumerate(TOP_STOCKS):
        logger.info(f"[{i+1}/{len(TOP_STOCKS)}] Fetching {symbol}...")

        data = fetch_stock_data(symbol)
        if data:
            save_to_database(conn, data)
            success_count += 1

        # Progress
        if (i + 1) % 10 == 0:
            logger.info(f"Progress: {i+1}/{len(TOP_STOCKS)} stocks processed")

    conn.close()
    logger.info(f"Import completed! {success_count}/{len(TOP_STOCKS)} stocks imported successfully")


if __name__ == "__main__":
    main()
