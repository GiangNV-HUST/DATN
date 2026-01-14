"""
Airflow DAG - Thu thập dữ liệu cổ phiếu
Scheduler: Chạy mỗi ngày vào lúc 15:30 chiều (sau khi thị trường đóng cửa)

Data Flow:
  VnStock API -> Kafka Producer -> Kafka Topic -> Enhanced Consumer -> Database

Database Tables Updated:
  - stock.stock_prices_1d (indicators)
  - stock_screener (screening data)
  - stock_1d (historical)
  - stock.stock_prices_3d_predict
  - stock.stock_prices_48d_predict
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os
import time
import pandas as pd

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vnstock import Vnstock
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
# Rate Limiting for VCI API
# =============================================================================

_last_api_call = 0
_API_DELAY = 3  # seconds between API calls


def rate_limit():
    """Apply rate limiting for API calls"""
    global _last_api_call
    elapsed = time.time() - _last_api_call
    if elapsed < _API_DELAY:
        sleep_time = _API_DELAY - elapsed
        time.sleep(sleep_time)
    _last_api_call = time.time()


def fetch_stock_data(ticker: str, days: int = 60) -> dict:
    """
    Fetch stock data from VnStock API with overview and fundamentals

    Returns:
        dict with keys: ticker, price_history, overview, fundamentals
    """
    rate_limit()

    try:
        stock = Vnstock().stock(symbol=ticker, source='VCI')

        # Get price history
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        price_df = stock.quote.history(
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval='1D'
        )

        if price_df is None or price_df.empty:
            return None

        # Rename columns to match expected format
        price_df = price_df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        # Handle time column
        if 'time' not in price_df.columns:
            if 'TradingDate' in price_df.columns:
                price_df['time'] = price_df['TradingDate']
            elif price_df.index.name == 'time' or isinstance(price_df.index, pd.DatetimeIndex):
                price_df = price_df.reset_index()
                if 'index' in price_df.columns:
                    price_df = price_df.rename(columns={'index': 'time'})

        # Get company overview (exchange, industry)
        # VnStock returns: icb_name3 for industry, symbol for ticker
        overview = {}
        try:
            rate_limit()
            overview_data = stock.company.overview()
            if overview_data is not None and not overview_data.empty:
                row = overview_data.iloc[0] if hasattr(overview_data, 'iloc') else {}
                # icb_name3 is the industry classification
                industry = row.get('icb_name3') or row.get('icb_name2') or row.get('industry')
                # Exchange is determined by ticker prefix or listing info
                overview = {
                    'exchange': 'HOSE',  # Default, most stocks are on HOSE
                    'industry': industry
                }
        except Exception:
            pass

        # Get fundamentals (PE, PB, ROE)
        # VnStock returns MultiIndex columns: ('Category', 'Metric')
        fundamentals = {}
        try:
            rate_limit()
            ratio_data = stock.finance.ratio(period='quarter', lang='en')
            if ratio_data is not None and not ratio_data.empty:
                # Flatten MultiIndex columns if present
                if isinstance(ratio_data.columns, pd.MultiIndex):
                    # Create a mapping from metric name to value
                    latest = ratio_data.iloc[-1]
                    ratio_dict = {}
                    for col in ratio_data.columns:
                        if isinstance(col, tuple):
                            metric_name = col[1]  # Get the metric name (second level)
                            ratio_dict[metric_name] = latest[col]
                        else:
                            ratio_dict[col] = latest[col]
                else:
                    ratio_dict = ratio_data.iloc[-1].to_dict()

                # Extract values using the actual column names from VnStock
                pe_val = ratio_dict.get('P/E') or ratio_dict.get('PE')
                pb_val = ratio_dict.get('P/B') or ratio_dict.get('PB')
                roe_val = ratio_dict.get('ROE (%)') or ratio_dict.get('ROE')
                eps_val = ratio_dict.get('EPS (VND)') or ratio_dict.get('EPS')
                div_val = ratio_dict.get('Dividend yield (%)') or ratio_dict.get('Dividend Yield')

                # Note: ROE from VnStock is in decimal form (0.1 = 10%), need to multiply by 100
                fundamentals = {
                    'pe': float(pe_val) if pe_val and not pd.isna(pe_val) else None,
                    'pb': float(pb_val) if pb_val and not pd.isna(pb_val) else None,
                    'roe': float(roe_val) * 100 if roe_val and not pd.isna(roe_val) else None,  # Convert to %
                    'eps': float(eps_val) if eps_val and not pd.isna(eps_val) else None,
                    'dividend_yield': float(div_val) if div_val and not pd.isna(div_val) else None
                }
        except Exception as e:
            print(f"Error getting fundamentals for {ticker}: {e}")

        # Convert timestamps to ISO format strings for JSON serialization
        price_records = price_df.to_dict(orient='records')
        for record in price_records:
            if 'time' in record and hasattr(record['time'], 'isoformat'):
                record['time'] = record['time'].isoformat()

        return {
            'ticker': ticker,
            'price_history': price_records,
            'overview': overview,
            'fundamentals': fundamentals,
            'fetched_at': datetime.now().isoformat()
        }

    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None


# =============================================================================
# Task function
# =============================================================================


def crawl_and_produce_batch(tickers, batch_name):
    """
    Crawl data và gửi vào kafka cho một batch

    Data format sent to Kafka:
        {
            'ticker': str,
            'price_history': list[dict],  # OHLCV data
            'overview': {'exchange': str, 'industry': str},
            'fundamentals': {'pe': float, 'pb': float, 'roe': float, ...},
            'fetched_at': str
        }

    Enhanced Consumer will:
        - Calculate technical indicators (RSI, MA, MACD, BB)
        - Detect alerts
        - Generate predictions (3d & 48d)
        - Save to: stock_prices_1d, stock_screener, stock_1d, predictions tables
    """
    print(f"{'='*60}")
    print(f"Processing batch: {batch_name}")
    print(f"Tickers: {tickers}")
    print(f"{'='* 60}")

    producer = StockDataProducer()

    success_count = 0
    failed_count = 0
    for ticker in tickers:
        try:
            print(f"📊 Crawling {ticker}...")

            # Fetch data with new format (includes overview & fundamentals)
            data = fetch_stock_data(ticker, days=60)

            if data is None:
                print(f"⚠️ No data for {ticker}")
                failed_count += 1
                continue

            # Gửi vào kafka với format mới
            success = producer.send_stock_data(ticker, data)

            if success:
                print(f"✅ {ticker} sent ({len(data['price_history'])} records)")
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

