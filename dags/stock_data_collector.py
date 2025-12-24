"""
Airflow DAG - Thu thập dữ liệu cổ phiếu
Scheduler: Chạy mỗi ngày vào lúc 9h sáng
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data_collector.vnstock_client import VnStockClient
from src.kafka_producer.producer import StockDataProducer

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
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "stock_data_collector",
    default_args=default_args,
    description="Crawl stock data và gửi vào kafka",
    schedule_interval="0 9 * * 1-5",
    catchup=False,
    tags=["stock", "phase"],
)

# ============================================================================
# DANH SÁCH CỔ PHIẾU
# ============================================================================

TICKERS_BATCH_1 = ["VNM", "VCB", "HPG", "VHM", "VIC"]
TICKERS_BATCH_2 = ["FPT", "MSN", "MWG", "VRE", "GAS"]
TICKERS_BATCH_3 = ["TCB", "BID", "CTG", "VPB", "POW"]

# =============================================================================
# Task function
# =============================================================================


def crawl_and_produce_batch(tickers, batch_name):
    """
    Crawl data và gửi vào kafka cho một batch

    Args:
        tickers: List các mã cổ phiếu
        batch_name: Tên batch (để logging)
    """
    print(f"{'='*60}")
    print(f"Processing batch: {batch_name}")
    print(f"Tickers: {tickers}")
    print(f"{'='* 60}")

    client = VnStockClient()
    producer = StockDataProducer()

    success_count = 0
    failed_count = 0
    for ticker in tickers:
        try:
            print(f"📊 Crawling {ticker}...")

            # Crawl data
            df = client.get_daily_data(ticker)

            if df is None or df.empty:
                print(f"⚠️ No data for {ticker}")
                failed_count += 1
                continue
            # Gửi vào kafka
            success = producer.send_stock_data(ticker, df)

            if success:
                print(f"✅ {ticker} sent successfully")
                success_count += 1
            else:
                print(f"❌ Failed to send {ticker}")
                failed_count += 1

        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            failed_count += 1

    # Đóng producer
    producer.close()

    # Summary
    print(f"\n{'='*60}")
    print(f"Batch {batch_name} Summary:")
    print(f"    Total: {len(tickers)}")
    print(f"    ✅ Success: {success_count}")
    print(f"    ❌ Failed: {failed_count}")
    print(f"{'='*60}")

    # Raise error nếu tất cả đều fail
    if success_count == 0 and len(tickers) > 0:
        raise Exception(f"All tickers in batch {batch_name} failed!")

    return {"batch": batch_name, "success": success_count, "failed": failed_count}


# ===============================================================================
# TASKS
# ===============================================================================

task_batch_1 = PythonOperator(
    task_id="crawl_batch_1",
    python_callable=crawl_and_produce_batch,
    op_kwargs={"tickers": TICKERS_BATCH_1, "batch_name": "Batch 1"},
    dag=dag,
)

task_batch_2 = PythonOperator(
    task_id="crawl_batch_2",
    python_callable=crawl_and_produce_batch,
    op_kwargs={"tickers": TICKERS_BATCH_2, "batch_name": "Batch 2"},
    dag=dag,
)

task_batch_3 = PythonOperator(
    task_id="crawl_batch_3",
    python_callable=crawl_and_produce_batch,
    op_kwargs={"tickers": TICKERS_BATCH_3, "batch_name": "Batch 3"},
    dag=dag,
)

# ==========================================================================
# Task Dependencies (chạy song song)
# ==========================================================================

[task_batch_1, task_batch_2, task_batch_3]

