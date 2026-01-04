"""
Airflow DAG - Thu thập dữ liệu intraday (1 phút)
Scheduler: Chạy end-of-day lúc 15:35 chiều để lấy toàn bộ data 1 phút của ngày
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data_collector.vnstock_client import VnStockClient
from src.database.connection import Database
import pandas as pd

# ================================================================================
# DAG Configuration
# ================================================================================

default_args = {
    "owner": "stock",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}

dag = DAG(
    "intraday_1m_collector",
    default_args=default_args,
    description="Crawl intraday 1-minute stock data - End of Day",
    schedule_interval="35 15 * * 1-5",  # 15:35 chiều (sau khi đóng cửa)
    catchup=False,
    tags=["stock", "intraday", "1m"],
)

# ============================================================================
# DANH SÁCH CỔ PHIẾU
# ============================================================================

TICKERS = ["VNM", "VCB", "HPG", "VHM", "VIC", "FPT", "MSN", "MWG", "VRE", "GAS", "TCB", "BID", "CTG", "VPB", "POW"]

# =============================================================================
# Helper Functions
# =============================================================================

def save_intraday_to_database(ticker, df):
    """
    Lưu dữ liệu intraday vào database

    Args:
        ticker: Mã cổ phiếu
        df: DataFrame với columns: time, open, high, low, close, volume

    Returns:
        bool: True nếu thành công
    """
    if df is None or df.empty:
        print(f"⚠️ No data to save for {ticker}")
        return False

    try:
        db = Database()
        db.connect()
        cursor = db.get_cursor()

        # Prepare data
        df['ticker'] = ticker

        # Ensure required columns exist
        required_cols = ['time', 'ticker', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                print(f"⚠️ Missing column {col} in data for {ticker}")
                return False

        # Select only required columns
        df_insert = df[required_cols].copy()

        # Convert to list of tuples
        values = [tuple(row) for row in df_insert.values]

        # Batch insert with ON CONFLICT
        insert_query = """
            INSERT INTO stock.stock_prices_1m (time, ticker, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (time, ticker) DO NOTHING
        """

        cursor.executemany(insert_query, values)
        db.conn.commit()

        inserted = cursor.rowcount
        print(f"✅ Saved {inserted} records to stock_prices_1m for {ticker}")
        db.close()
        return True

    except Exception as e:
        print(f"❌ Error saving to database for {ticker}: {e}")
        if db and db.conn:
            db.conn.rollback()
            db.close()
        return False

# =============================================================================
# Task Function
# =============================================================================

def crawl_intraday_1m():
    """
    Crawl dữ liệu 1 phút cho tất cả tickers
    Chạy vào cuối ngày để lấy toàn bộ data của ngày hôm đó
    """
    print(f"{'='*60}")
    print(f"Crawling Intraday 1-minute Data")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*60}")

    client = VnStockClient()
    success_count = 0
    failed_count = 0
    total_records = 0

    for ticker in TICKERS:
        try:
            print(f"\n📊 Crawling 1m data for {ticker}...")

            # Get intraday data (1-minute interval)
            # date=None means today
            df = client.get_intraday_data(ticker, date=None, interval="1m")

            if df is not None and not df.empty:
                # Rename 'time' column if it's named differently
                if 'time' not in df.columns and 'datetime' in df.columns:
                    df = df.rename(columns={'datetime': 'time'})
                elif 'time' not in df.columns and df.index.name in ['time', 'datetime']:
                    df = df.reset_index()
                    if 'datetime' in df.columns:
                        df = df.rename(columns={'datetime': 'time'})

                # Save to database
                saved = save_intraday_to_database(ticker, df)

                if saved:
                    success_count += 1
                    total_records += len(df)
                    print(f"✅ {ticker}: {len(df)} records")
                else:
                    failed_count += 1
                    print(f"❌ {ticker}: Failed to save")
            else:
                failed_count += 1
                print(f"⚠️ {ticker}: No data available")

        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            failed_count += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Intraday 1m Collection Summary:")
    print(f"    Total Tickers: {len(TICKERS)}")
    print(f"    ✅ Success: {success_count}/{len(TICKERS)}")
    print(f"    ❌ Failed: {failed_count}/{len(TICKERS)}")
    print(f"    📊 Total Records: {total_records}")
    print(f"    📈 Avg Records/Ticker: {total_records // success_count if success_count > 0 else 0}")
    print(f"{'='*60}")

    # Raise error nếu tất cả đều fail
    if success_count == 0 and len(TICKERS) > 0:
        raise Exception("All tickers failed to collect intraday data!")

    return {
        "success": success_count,
        "failed": failed_count,
        "total_records": total_records
    }


# ===============================================================================
# TASK
# ===============================================================================

task_crawl_1m = PythonOperator(
    task_id="crawl_intraday_1m",
    python_callable=crawl_intraday_1m,
    dag=dag,
)

# Single task - no dependencies needed
task_crawl_1m
