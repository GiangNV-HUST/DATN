"""
Script để populate bảng stock.stock_screener từ dữ liệu hiện có

Chạy một lần để điền dữ liệu ban đầu, sau đó DAG sẽ tự động cập nhật hàng ngày.

Usage:
    python scripts/populate_stock_screener.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )


def populate_from_existing_data():
    """
    Populate stock_screener từ dữ liệu có sẵn trong stock_prices_1d và ratio tables
    """
    conn = get_connection()
    cur = conn.cursor()

    logger.info("=" * 60)
    logger.info("POPULATING stock.stock_screener FROM EXISTING DATA")
    logger.info("=" * 60)

    try:
        # Get latest price data for each ticker from stock_prices_1d
        logger.info("Fetching latest price data from stock_prices_1d...")

        cur.execute("""
            WITH latest_prices AS (
                SELECT DISTINCT ON (ticker)
                    ticker,
                    time,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    ma5,
                    ma10,
                    ma20,
                    ma50,
                    rsi
                FROM stock.stock_prices_1d
                WHERE time >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY ticker, time DESC
            ),
            prev_prices AS (
                SELECT DISTINCT ON (ticker)
                    ticker,
                    close as prev_close
                FROM stock.stock_prices_1d
                WHERE time >= CURRENT_DATE - INTERVAL '14 days'
                  AND time < (SELECT MAX(time) FROM stock.stock_prices_1d WHERE ticker = stock.stock_prices_1d.ticker)
                ORDER BY ticker, time DESC
            ),
            avg_values AS (
                SELECT
                    ticker,
                    AVG(close * volume) as avg_trading_value_20d
                FROM stock.stock_prices_1d
                WHERE time >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY ticker
            )
            SELECT
                lp.ticker,
                lp.open,
                lp.high,
                lp.low,
                lp.close,
                lp.volume,
                lp.ma5,
                lp.ma10,
                lp.ma20,
                lp.ma50,
                lp.rsi as rsi14,
                CASE WHEN pp.prev_close > 0
                     THEN ((lp.close - pp.prev_close) / pp.prev_close * 100)
                     ELSE NULL
                END as change_percent_1d,
                av.avg_trading_value_20d
            FROM latest_prices lp
            LEFT JOIN prev_prices pp ON lp.ticker = pp.ticker
            LEFT JOIN avg_values av ON lp.ticker = av.ticker;
        """)

        price_data = cur.fetchall()
        logger.info(f"Found {len(price_data)} tickers with price data")

        # Get fundamental data from ratio table
        logger.info("Fetching fundamental data from ratio table...")

        cur.execute("""
            SELECT DISTINCT ON (ticker)
                ticker,
                pe,
                pb,
                roe,
                eps
            FROM stock.ratio
            ORDER BY ticker, year DESC, quarter DESC;
        """)

        ratio_data = {row[0]: {'pe': row[1], 'pb': row[2], 'roe': row[3], 'eps': row[4]}
                      for row in cur.fetchall()}
        logger.info(f"Found {len(ratio_data)} tickers with ratio data")

        # Get industry data from information table
        logger.info("Fetching industry data from information table...")

        cur.execute("""
            SELECT ticker, exchange, industry
            FROM stock.information;
        """)

        info_data = {row[0]: {'exchange': row[1], 'industry': row[2]}
                     for row in cur.fetchall()}
        logger.info(f"Found {len(info_data)} tickers with information data")

        # Insert into stock_screener
        logger.info("Inserting data into stock.stock_screener...")

        inserted = 0
        for row in price_data:
            ticker = row[0]

            # Get additional data
            ratio = ratio_data.get(ticker, {})
            info = info_data.get(ticker, {})

            try:
                cur.execute("""
                    INSERT INTO stock.stock_screener
                    (ticker, exchange, industry, close, open, high, low, volume,
                     change_percent_1d, pe, pb, roe, eps,
                     rsi14, ma5, ma10, ma20, ma50, avg_trading_value_20d, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticker) DO UPDATE SET
                        exchange = EXCLUDED.exchange,
                        industry = EXCLUDED.industry,
                        close = EXCLUDED.close,
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        volume = EXCLUDED.volume,
                        change_percent_1d = EXCLUDED.change_percent_1d,
                        pe = EXCLUDED.pe,
                        pb = EXCLUDED.pb,
                        roe = EXCLUDED.roe,
                        eps = EXCLUDED.eps,
                        rsi14 = EXCLUDED.rsi14,
                        ma5 = EXCLUDED.ma5,
                        ma10 = EXCLUDED.ma10,
                        ma20 = EXCLUDED.ma20,
                        ma50 = EXCLUDED.ma50,
                        avg_trading_value_20d = EXCLUDED.avg_trading_value_20d,
                        updated_at = EXCLUDED.updated_at
                """, (
                    ticker,                          # ticker
                    info.get('exchange'),            # exchange
                    info.get('industry'),            # industry
                    row[4],                          # close
                    row[1],                          # open
                    row[2],                          # high
                    row[3],                          # low
                    row[5],                          # volume
                    row[11],                         # change_percent_1d
                    ratio.get('pe'),                 # pe
                    ratio.get('pb'),                 # pb
                    ratio.get('roe'),                # roe
                    ratio.get('eps'),                # eps
                    row[10],                         # rsi14
                    row[6],                          # ma5
                    row[7],                          # ma10
                    row[8],                          # ma20
                    row[9],                          # ma50
                    row[12],                         # avg_trading_value_20d
                    datetime.now()                   # updated_at
                ))
                inserted += 1
            except Exception as e:
                logger.error(f"Error inserting {ticker}: {e}")
                continue

        conn.commit()
        logger.info(f"✅ Inserted/Updated {inserted} records into stock.stock_screener")

        # Verify data
        cur.execute("SELECT COUNT(*) FROM stock.stock_screener;")
        total = cur.fetchone()[0]
        logger.info(f"✅ Total records in stock.stock_screener: {total}")

        # Show sample
        cur.execute("""
            SELECT ticker, close, change_percent_1d, pe, roe, rsi14, industry
            FROM stock.stock_screener
            ORDER BY avg_trading_value_20d DESC NULLS LAST
            LIMIT 10;
        """)

        logger.info("\nTop 10 stocks by trading value:")
        logger.info("-" * 80)
        for row in cur.fetchall():
            logger.info(f"  {row[0]:6} | Close: {row[1]:>10} | Change: {row[2]:>7.2f}% | PE: {row[3] or 'N/A':>6} | ROE: {row[4] or 'N/A':>6} | RSI: {row[5] or 'N/A':>5} | {row[6] or 'N/A'}")

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    populate_from_existing_data()
