"""
Airflow DAG - Thu thập dữ liệu realtime theo phút
Scheduler: Chạy mỗi phút trong giờ giao dịch (9:00-11:30 và 13:00-15:00)

Mục đích: Khi user hỏi giá lúc 9:20:30 → Lấy từ bảng dữ liệu của 9:20
"""

from airflow import DAG
from airflow.operators.python import PythonOperator, ShortCircuitOperator
from datetime import datetime, timedelta
import sys
import os
import pytz

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Vietnam timezone
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# ================================================================================
# DAG Configuration
# ================================================================================

default_args = {
    "owner": "stock",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    "realtime_1m_collector",
    default_args=default_args,
    description="Crawl realtime stock data every minute during trading hours",
    schedule_interval="* 9-11,13-14 * * 1-5",  # Mỗi phút, 9-11h và 13-14h, T2-T6
    catchup=False,
    max_active_runs=1,  # Chỉ chạy 1 instance tại 1 thời điểm
    tags=["stock", "realtime", "1m", "intraday"],
)

# ============================================================================
# DANH SÁCH CỔ PHIẾU VN30
# ============================================================================

VN30_STOCKS = [
    'ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB', 'HPG',
    'MBB', 'MSN', 'MWG', 'PLX', 'LPB', 'SAB', 'SHB', 'SSB', 'SSI', 'STB',
    'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC', 'VNM', 'VPB', 'VRE'
]

# =============================================================================
# Helper Functions
# =============================================================================

def is_trading_hours():
    """
    Kiểm tra có đang trong giờ giao dịch không (theo giờ Việt Nam)
    Phiên sáng: 9:00 - 11:30
    Phiên chiều: 13:00 - 15:00
    """
    # Lấy thời gian hiện tại theo timezone Việt Nam
    now_vn = datetime.now(VN_TZ)
    current_time = now_vn.time()

    from datetime import time as dt_time

    # Phiên sáng: 9:00 - 11:30
    morning_start = dt_time(9, 0)
    morning_end = dt_time(11, 30)

    # Phiên chiều: 13:00 - 15:00
    afternoon_start = dt_time(13, 0)
    afternoon_end = dt_time(15, 0)

    in_morning = morning_start <= current_time <= morning_end
    in_afternoon = afternoon_start <= current_time <= afternoon_end

    return in_morning or in_afternoon


def check_trading_hours(**context):
    """
    ShortCircuit: Chỉ chạy nếu đang trong giờ giao dịch
    """
    is_trading = is_trading_hours()
    now_vn = datetime.now(VN_TZ)

    if is_trading:
        print(f"✅ Trong giờ giao dịch - {now_vn.strftime('%H:%M:%S')} (VN)")
    else:
        print(f"⏸️ Ngoài giờ giao dịch - {now_vn.strftime('%H:%M:%S')} (VN)")

    return is_trading


def fetch_and_save_realtime_data(**context):
    """
    Lấy dữ liệu realtime từ VCI và lưu vào database
    """
    from vnstock import Vnstock
    from src.database.connection import Database
    import pandas as pd

    now_vn = datetime.now(VN_TZ)
    print(f"{'='*60}")
    print(f"Fetching realtime data at {now_vn.strftime('%Y-%m-%d %H:%M:%S')} (VN)")
    print(f"{'='*60}")

    db = Database()
    db.connect()
    cursor = db.get_cursor()

    success_count = 0
    failed_count = 0

    # Lấy timestamp hiện tại (làm tròn xuống phút) - timezone VN
    current_minute = now_vn.replace(second=0, microsecond=0)

    for symbol in VN30_STOCKS:
        try:
            # Lấy dữ liệu intraday từ VCI
            stock = Vnstock().stock(symbol=symbol.upper(), source='VCI')
            intraday = stock.quote.intraday()

            if intraday is not None and not intraday.empty:
                # Lấy record mới nhất
                latest = intraday.iloc[-1]

                # Chuẩn bị dữ liệu
                price = float(latest.get('price', latest.get('close', 0)))
                volume = int(latest.get('volume', latest.get('vol', 0)))

                # Insert vào database
                cursor.execute("""
                    INSERT INTO stock.stock_prices_1m (time, ticker, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (time, ticker) DO UPDATE SET
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume
                """, (
                    current_minute,
                    symbol.upper(),
                    price,  # open = current price (simplified)
                    price,  # high = current price
                    price,  # low = current price
                    price,  # close = current price
                    volume
                ))

                success_count += 1

            else:
                print(f"⚠️ No data for {symbol}")
                failed_count += 1

        except Exception as e:
            print(f"❌ Error fetching {symbol}: {e}")
            failed_count += 1

    # Commit tất cả
    db.connection.commit()
    db.close()

    print(f"\n{'='*60}")
    print(f"Summary at {current_minute.strftime('%H:%M')}:")
    print(f"  ✅ Success: {success_count}/{len(VN30_STOCKS)}")
    print(f"  ❌ Failed: {failed_count}/{len(VN30_STOCKS)}")
    print(f"{'='*60}")

    return {
        "timestamp": current_minute.isoformat(),
        "success": success_count,
        "failed": failed_count
    }


# ===============================================================================
# TASKS
# ===============================================================================

# Task 1: Kiểm tra giờ giao dịch (ShortCircuit - skip nếu ngoài giờ)
task_check_trading_hours = ShortCircuitOperator(
    task_id="check_trading_hours",
    python_callable=check_trading_hours,
    dag=dag,
)

# Task 2: Lấy và lưu dữ liệu
task_fetch_data = PythonOperator(
    task_id="fetch_and_save_realtime_data",
    python_callable=fetch_and_save_realtime_data,
    dag=dag,
)

# ==========================================================================
# Task Dependencies
# ==========================================================================

task_check_trading_hours >> task_fetch_data
