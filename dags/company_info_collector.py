"""
Airflow DAG - Thu thập thông tin công ty
Scheduler: Chạy ngày 1 hàng tháng lúc 00h
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os
import json

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
    "company_info_collector",
    default_args=default_args,
    description="Crawl thông tin công ty (Profile, Overview, Officers, Shareholders)",
    schedule_interval="0 0 1 * *",  # 00h ngày 1 hàng tháng
    catchup=False,
    tags=["stock", "company", "information"],
)

# ============================================================================
# DANH SÁCH CỔ PHIẾU
# ============================================================================

TICKERS = ["VNM", "VCB", "HPG", "VHM", "VIC", "FPT", "MSN", "MWG", "VRE", "GAS", "TCB", "BID", "CTG", "VPB", "POW"]

# =============================================================================
# Task Functions
# =============================================================================

def crawl_company_profile():
    """Crawl company profile cho tất cả tickers"""
    print(f"{'='*60}")
    print(f"Crawling Company Profile")
    print(f"{'='*60}")

    client = VnStockClient()
    db = Database()
    db.connect()
    cursor = db.get_cursor()

    success_count = 0
    failed_count = 0

    for ticker in TICKERS:
        try:
            print(f"📊 Crawling profile for {ticker}...")
            data = client.get_company_profile(ticker)

            if data is not None:
                # Convert to dict if DataFrame
                if isinstance(data, pd.DataFrame):
                    data_dict = data.to_dict('records')[0] if not data.empty else {}
                else:
                    data_dict = data

                # Save to database
                cursor.execute("""
                    INSERT INTO stock.information (ticker, profile_data, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (ticker)
                    DO UPDATE SET
                        profile_data = EXCLUDED.profile_data,
                        updated_at = EXCLUDED.updated_at
                """, (ticker, json.dumps(data_dict), datetime.now()))

                db.conn.commit()
                print(f"✅ Saved profile for {ticker}")
                success_count += 1
            else:
                failed_count += 1

        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            failed_count += 1
            db.conn.rollback()

    db.close()

    print(f"\n{'='*60}")
    print(f"Company Profile Summary:")
    print(f"    ✅ Success: {success_count}/{len(TICKERS)}")
    print(f"    ❌ Failed: {failed_count}/{len(TICKERS)}")
    print(f"{'='*60}")

    return {"success": success_count, "failed": failed_count}


def crawl_company_overview():
    """Crawl company overview cho tất cả tickers"""
    print(f"{'='*60}")
    print(f"Crawling Company Overview")
    print(f"{'='*60}")

    client = VnStockClient()
    db = Database()
    db.connect()
    cursor = db.get_cursor()

    success_count = 0
    failed_count = 0

    for ticker in TICKERS:
        try:
            print(f"📊 Crawling overview for {ticker}...")
            data = client.get_company_overview(ticker)

            if data is not None:
                # Convert to dict if DataFrame
                if isinstance(data, pd.DataFrame):
                    data_dict = data.to_dict('records')[0] if not data.empty else {}
                else:
                    data_dict = data

                # Save to database
                cursor.execute("""
                    INSERT INTO stock.information (ticker, overview_data, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (ticker)
                    DO UPDATE SET
                        overview_data = EXCLUDED.overview_data,
                        updated_at = EXCLUDED.updated_at
                """, (ticker, json.dumps(data_dict), datetime.now()))

                db.conn.commit()
                print(f"✅ Saved overview for {ticker}")
                success_count += 1
            else:
                failed_count += 1

        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            failed_count += 1
            db.conn.rollback()

    db.close()

    print(f"\n{'='*60}")
    print(f"Company Overview Summary:")
    print(f"    ✅ Success: {success_count}/{len(TICKERS)}")
    print(f"    ❌ Failed: {failed_count}/{len(TICKERS)}")
    print(f"{'='*60}")

    return {"success": success_count, "failed": failed_count}


def crawl_company_officers():
    """Crawl company officers cho tất cả tickers"""
    print(f"{'='*60}")
    print(f"Crawling Company Officers")
    print(f"{'='*60}")

    client = VnStockClient()
    db = Database()
    db.connect()
    cursor = db.get_cursor()

    success_count = 0
    failed_count = 0

    for ticker in TICKERS:
        try:
            print(f"📊 Crawling officers for {ticker}...")
            df = client.get_company_officers(ticker)

            if df is not None and not df.empty:
                # Save to database
                data_dict = df.to_dict('records')
                cursor.execute("""
                    INSERT INTO stock.information (ticker, officers_data, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (ticker)
                    DO UPDATE SET
                        officers_data = EXCLUDED.officers_data,
                        updated_at = EXCLUDED.updated_at
                """, (ticker, json.dumps(data_dict), datetime.now()))

                db.conn.commit()
                print(f"✅ Saved officers for {ticker}: {len(df)} records")
                success_count += 1
            else:
                failed_count += 1

        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            failed_count += 1
            db.conn.rollback()

    db.close()

    print(f"\n{'='*60}")
    print(f"Company Officers Summary:")
    print(f"    ✅ Success: {success_count}/{len(TICKERS)}")
    print(f"    ❌ Failed: {failed_count}/{len(TICKERS)}")
    print(f"{'='*60}")

    return {"success": success_count, "failed": failed_count}


def crawl_company_shareholders():
    """Crawl company shareholders cho tất cả tickers"""
    print(f"{'='*60}")
    print(f"Crawling Company Shareholders")
    print(f"{'='*60}")

    client = VnStockClient()
    db = Database()
    db.connect()
    cursor = db.get_cursor()

    success_count = 0
    failed_count = 0

    for ticker in TICKERS:
        try:
            print(f"📊 Crawling shareholders for {ticker}...")
            df = client.get_company_shareholders(ticker)

            if df is not None and not df.empty:
                # Save to database
                data_dict = df.to_dict('records')
                cursor.execute("""
                    INSERT INTO stock.information (ticker, shareholders_data, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (ticker)
                    DO UPDATE SET
                        shareholders_data = EXCLUDED.shareholders_data,
                        updated_at = EXCLUDED.updated_at
                """, (ticker, json.dumps(data_dict), datetime.now()))

                db.conn.commit()
                print(f"✅ Saved shareholders for {ticker}: {len(df)} records")
                success_count += 1
            else:
                failed_count += 1

        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            failed_count += 1
            db.conn.rollback()

    db.close()

    print(f"\n{'='*60}")
    print(f"Company Shareholders Summary:")
    print(f"    ✅ Success: {success_count}/{len(TICKERS)}")
    print(f"    ❌ Failed: {failed_count}/{len(TICKERS)}")
    print(f"{'='*60}")

    return {"success": success_count, "failed": failed_count}


# ===============================================================================
# TASKS
# ===============================================================================

task_profile = PythonOperator(
    task_id="crawl_company_profile",
    python_callable=crawl_company_profile,
    dag=dag,
)

task_overview = PythonOperator(
    task_id="crawl_company_overview",
    python_callable=crawl_company_overview,
    dag=dag,
)

task_officers = PythonOperator(
    task_id="crawl_company_officers",
    python_callable=crawl_company_officers,
    dag=dag,
)

task_shareholders = PythonOperator(
    task_id="crawl_company_shareholders",
    python_callable=crawl_company_shareholders,
    dag=dag,
)

# ==========================================================================
# Task Dependencies - Chạy tuần tự
# ==========================================================================

task_profile >> task_overview >> task_officers >> task_shareholders
