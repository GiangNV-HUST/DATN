"""
Airflow DAG - Thu thập báo cáo tài chính
Scheduler: Chạy mỗi tuần vào thứ 2 lúc 10h sáng
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
    "financial_reports_collector",
    default_args=default_args,
    description="Crawl báo cáo tài chính (Balance Sheet, Cash Flow, Income Statement, Ratios)",
    schedule_interval="0 10 * * 1",  # 10h sáng thứ 2 hàng tuần
    catchup=False,
    tags=["stock", "financial", "reports"],
)

# ============================================================================
# DANH SÁCH CỔ PHIẾU
# ============================================================================

TICKERS = ["VNM", "VCB", "HPG", "VHM", "VIC", "FPT", "MSN", "MWG", "VRE", "GAS", "TCB", "BID", "CTG", "VPB", "POW"]

# =============================================================================
# Helper Functions
# =============================================================================

def save_to_database(ticker, data, table_name, period):
    """
    Lưu dữ liệu vào database

    Args:
        ticker: Mã cổ phiếu
        data: DataFrame
        table_name: Tên bảng
        period: 'quarter' hoặc 'year'
    """
    if data is None or data.empty:
        print(f"⚠️ No data to save for {ticker} ({period})")
        return False

    try:
        db = Database()
        db.connect()
        cursor = db.get_cursor()

        # Add ticker and period columns
        data['ticker'] = ticker
        data['period_type'] = period
        data['updated_at'] = datetime.now()

        # Convert DataFrame to list of tuples
        columns = list(data.columns)
        values = [tuple(row) for row in data.values]

        # Generate INSERT statement
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join(columns)

        insert_query = f"""
            INSERT INTO stock.{table_name} ({columns_str})
            VALUES ({placeholders})
            ON CONFLICT (ticker, period_type, report_date)
            DO UPDATE SET updated_at = EXCLUDED.updated_at
        """

        # Execute batch insert
        cursor.executemany(insert_query, values)
        db.conn.commit()

        print(f"✅ Saved {len(values)} records to {table_name} for {ticker} ({period})")
        db.close()
        return True

    except Exception as e:
        print(f"❌ Error saving to database: {e}")
        if db and db.conn:
            db.conn.rollback()
            db.close()
        return False

# =============================================================================
# Task Functions
# =============================================================================

def crawl_balance_sheet(period='quarter'):
    """
    Crawl Balance Sheet cho tất cả tickers

    Args:
        period: 'quarter' hoặc 'year'
    """
    print(f"{'='*60}")
    print(f"Crawling Balance Sheet ({period})")
    print(f"{'='*60}")

    client = VnStockClient()
    success_count = 0
    failed_count = 0

    for ticker in TICKERS:
        try:
            print(f"📊 Crawling Balance Sheet for {ticker} ({period})...")
            df = client.get_balance_sheet(ticker, period=period)

            if df is not None and not df.empty:
                # Save to database
                saved = save_to_database(ticker, df, 'balance_sheet', period)
                if saved:
                    success_count += 1
                else:
                    failed_count += 1
            else:
                failed_count += 1

        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            failed_count += 1

    print(f"\n{'='*60}")
    print(f"Balance Sheet ({period}) Summary:")
    print(f"    ✅ Success: {success_count}/{len(TICKERS)}")
    print(f"    ❌ Failed: {failed_count}/{len(TICKERS)}")
    print(f"{'='*60}")

    return {"success": success_count, "failed": failed_count}


def crawl_cash_flow(period='quarter'):
    """
    Crawl Cash Flow cho tất cả tickers

    Args:
        period: 'quarter' hoặc 'year'
    """
    print(f"{'='*60}")
    print(f"Crawling Cash Flow ({period})")
    print(f"{'='*60}")

    client = VnStockClient()
    success_count = 0
    failed_count = 0

    for ticker in TICKERS:
        try:
            print(f"📊 Crawling Cash Flow for {ticker} ({period})...")
            df = client.get_cash_flow(ticker, period=period)

            if df is not None and not df.empty:
                saved = save_to_database(ticker, df, 'cash_flow', period)
                if saved:
                    success_count += 1
                else:
                    failed_count += 1
            else:
                failed_count += 1

        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            failed_count += 1

    print(f"\n{'='*60}")
    print(f"Cash Flow ({period}) Summary:")
    print(f"    ✅ Success: {success_count}/{len(TICKERS)}")
    print(f"    ❌ Failed: {failed_count}/{len(TICKERS)}")
    print(f"{'='*60}")

    return {"success": success_count, "failed": failed_count}


def crawl_income_statement(period='quarter'):
    """
    Crawl Income Statement cho tất cả tickers

    Args:
        period: 'quarter' hoặc 'year'
    """
    print(f"{'='*60}")
    print(f"Crawling Income Statement ({period})")
    print(f"{'='*60}")

    client = VnStockClient()
    success_count = 0
    failed_count = 0

    for ticker in TICKERS:
        try:
            print(f"📊 Crawling Income Statement for {ticker} ({period})...")
            df = client.get_income_statement(ticker, period=period)

            if df is not None and not df.empty:
                saved = save_to_database(ticker, df, 'income_statement', period)
                if saved:
                    success_count += 1
                else:
                    failed_count += 1
            else:
                failed_count += 1

        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            failed_count += 1

    print(f"\n{'='*60}")
    print(f"Income Statement ({period}) Summary:")
    print(f"    ✅ Success: {success_count}/{len(TICKERS)}")
    print(f"    ❌ Failed: {failed_count}/{len(TICKERS)}")
    print(f"{'='*60}")

    return {"success": success_count, "failed": failed_count}


def crawl_financial_ratios(period='quarter'):
    """
    Crawl Financial Ratios cho tất cả tickers

    Args:
        period: 'quarter' hoặc 'year'
    """
    print(f"{'='*60}")
    print(f"Crawling Financial Ratios ({period})")
    print(f"{'='*60}")

    client = VnStockClient()
    success_count = 0
    failed_count = 0

    for ticker in TICKERS:
        try:
            print(f"📊 Crawling Financial Ratios for {ticker} ({period})...")
            df = client.get_financial_ratios(ticker, period=period)

            if df is not None and not df.empty:
                saved = save_to_database(ticker, df, 'ratio', period)
                if saved:
                    success_count += 1
                else:
                    failed_count += 1
            else:
                failed_count += 1

        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            failed_count += 1

    print(f"\n{'='*60}")
    print(f"Financial Ratios ({period}) Summary:")
    print(f"    ✅ Success: {success_count}/{len(TICKERS)}")
    print(f"    ❌ Failed: {failed_count}/{len(TICKERS)}")
    print(f"{'='*60}")

    return {"success": success_count, "failed": failed_count}


# ===============================================================================
# TASKS - QUARTERLY DATA
# ===============================================================================

task_balance_sheet_quarterly = PythonOperator(
    task_id="crawl_balance_sheet_quarterly",
    python_callable=crawl_balance_sheet,
    op_kwargs={"period": "quarter"},
    dag=dag,
)

task_cash_flow_quarterly = PythonOperator(
    task_id="crawl_cash_flow_quarterly",
    python_callable=crawl_cash_flow,
    op_kwargs={"period": "quarter"},
    dag=dag,
)

task_income_statement_quarterly = PythonOperator(
    task_id="crawl_income_statement_quarterly",
    python_callable=crawl_income_statement,
    op_kwargs={"period": "quarter"},
    dag=dag,
)

task_ratios_quarterly = PythonOperator(
    task_id="crawl_ratios_quarterly",
    python_callable=crawl_financial_ratios,
    op_kwargs={"period": "quarter"},
    dag=dag,
)

# ===============================================================================
# TASKS - YEARLY DATA
# ===============================================================================

task_balance_sheet_yearly = PythonOperator(
    task_id="crawl_balance_sheet_yearly",
    python_callable=crawl_balance_sheet,
    op_kwargs={"period": "year"},
    dag=dag,
)

task_cash_flow_yearly = PythonOperator(
    task_id="crawl_cash_flow_yearly",
    python_callable=crawl_cash_flow,
    op_kwargs={"period": "year"},
    dag=dag,
)

task_income_statement_yearly = PythonOperator(
    task_id="crawl_income_statement_yearly",
    python_callable=crawl_income_statement,
    op_kwargs={"period": "year"},
    dag=dag,
)

task_ratios_yearly = PythonOperator(
    task_id="crawl_ratios_yearly",
    python_callable=crawl_financial_ratios,
    op_kwargs={"period": "year"},
    dag=dag,
)

# ==========================================================================
# Task Dependencies
# Quarterly tasks chạy song song, sau đó chạy yearly tasks
# ==========================================================================

quarterly_tasks = [
    task_balance_sheet_quarterly,
    task_cash_flow_quarterly,
    task_income_statement_quarterly,
    task_ratios_quarterly,
]

yearly_tasks = [
    task_balance_sheet_yearly,
    task_cash_flow_yearly,
    task_income_statement_yearly,
    task_ratios_yearly,
]

# Quarterly tasks và yearly tasks chạy song song (không phụ thuộc nhau)
# Nếu muốn chạy tuần tự, dùng chain:
# from airflow.models.baseoperator import chain
# chain(*quarterly_tasks, *yearly_tasks)
