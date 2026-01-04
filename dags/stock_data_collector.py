"""
Airflow DAG - Thu thập dữ liệu cổ phiếu
Scheduler: Chạy mỗi ngày vào lúc 15:30 chiều (sau khi thị trường đóng cửa)
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
    description="Crawl daily stock data - End of Day (sau khi thị trường đóng cửa)",
    schedule_interval="30 15 * * 1-5",  # 15:30 chiều (sau khi đóng cửa)
    catchup=False,
    tags=["stock", "daily", "eod"],
)

# ============================================================================
# DANH SÁCH 50 CỔ PHIẾU (VN30 + VNMidcap phổ biến)
# ============================================================================

# Batch 1: Top 10 Ngân hàng & Tài chính
TICKERS_BATCH_1 = ["VCB", "BID", "CTG", "VPB", "TCB", "MBB", "ACB", "STB", "HDB", "SSI"]

# Batch 2: Top 10 Bất động sản & Xây dựng
TICKERS_BATCH_2 = ["VHM", "VIC", "VRE", "NVL", "PDR", "DXG", "KDH", "HDC", "DIG", "BCM"]

# Batch 3: Top 10 Thực phẩm & Tiêu dùng
TICKERS_BATCH_3 = ["VNM", "MSN", "MWG", "SAB", "VHC", "FRT", "MCH", "ASM", "DGW", "PNJ"]

# Batch 4: Top 10 Công nghiệp & Năng lượng
TICKERS_BATCH_4 = ["HPG", "GAS", "POW", "PLX", "PVD", "PVS", "PVT", "GEG", "NT2", "REE"]

# Batch 5: Top 10 Công nghệ & Dịch vụ
TICKERS_BATCH_5 = ["FPT", "VGC", "GMD", "SHB", "EVF", "VCI", "VIX", "HCM", "CMG", "ITD"]

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
# TASKS - 5 batches chạy song song
# ===============================================================================

task_batch_1 = PythonOperator(
    task_id="crawl_batch_1",
    python_callable=crawl_and_produce_batch,
    op_kwargs={"tickers": TICKERS_BATCH_1, "batch_name": "Batch 1 - Banks"},
    dag=dag,
)

task_batch_2 = PythonOperator(
    task_id="crawl_batch_2",
    python_callable=crawl_and_produce_batch,
    op_kwargs={"tickers": TICKERS_BATCH_2, "batch_name": "Batch 2 - Real Estate"},
    dag=dag,
)

task_batch_3 = PythonOperator(
    task_id="crawl_batch_3",
    python_callable=crawl_and_produce_batch,
    op_kwargs={"tickers": TICKERS_BATCH_3, "batch_name": "Batch 3 - Consumer"},
    dag=dag,
)

task_batch_4 = PythonOperator(
    task_id="crawl_batch_4",
    python_callable=crawl_and_produce_batch,
    op_kwargs={"tickers": TICKERS_BATCH_4, "batch_name": "Batch 4 - Industry"},
    dag=dag,
)

task_batch_5 = PythonOperator(
    task_id="crawl_batch_5",
    python_callable=crawl_and_produce_batch,
    op_kwargs={"tickers": TICKERS_BATCH_5, "batch_name": "Batch 5 - Technology"},
    dag=dag,
)

# All batches run in parallel (no dependencies)
# Airflow will execute them concurrently based on available workers

# ==========================================================================
# Task Dependencies (chạy song song)
# ==========================================================================

[task_batch_1, task_batch_2, task_batch_3]

