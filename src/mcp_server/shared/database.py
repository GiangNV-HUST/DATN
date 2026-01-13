"""
Database utilities for MCP implementation
Shared module for both MCP server and client
"""
import os
import logging
import psycopg2
from typing import Dict, Any, Optional, Tuple, List
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# VN30 Stock List
VN30_STOCKS = {
    'ACB': 'Ngân hàng TMCP Á Châu',
    'BCM': 'Tổng Công ty Đầu tư và Phát triển Công nghiệp',
    'BID': 'Ngân hàng TMCP Đầu tư và Phát triển Việt Nam',
    'BVH': 'Tập đoàn Bảo Việt',
    'CTG': 'Ngân hàng TMCP Công thương Việt Nam',
    'FPT': 'Công ty Cổ phần FPT',
    'GAS': 'Tổng Công ty Khí Việt Nam',
    'GVR': 'Tập đoàn Công nghiệp Cao su Việt Nam',
    'HDB': 'Ngân hàng TMCP Phát Triển TP.HCM',
    'HPG': 'Công ty CP Tập đoàn Hòa Phát',
    'MBB': 'Ngân hàng TMCP Quân đội',
    'MSN': 'Công ty CP Tập đoàn Masan',
    'MWG': 'Công ty CP Đầu tư Thế Giới Di Động',
    'PLX': 'Tập đoàn Xăng dầu Việt Nam',
    'LPB': 'Ngân hàng TMCP Lộc Phát Việt Nam',
    'SAB': 'TỔNG CTCP Bia - Rượu - NGK Sài Gòn',
    'SHB': 'Ngân hàng TMCP Sài Gòn – Hà Nội',
    'SSB': 'Ngân hàng TMCP Đông Nam Á',
    'SSI': 'Công ty CP Chứng khoán SSI',
    'STB': 'Ngân hàng TMCP Sài Gòn Thương Tín',
    'TCB': 'Ngân hàng TMCP Kỹ thương Việt Nam',
    'TPB': 'Ngân hàng TMCP Tiên Phong',
    'VCB': 'Ngân hàng TMCP Ngoại thương Việt Nam',
    'VHM': 'Công ty CP Vinhomes',
    'VIB': 'Ngân hàng TMCP Quốc tế Việt Nam',
    'VIC': 'Tập đoàn Vingroup',
    'VJC': 'Công ty CP Hàng không Vietjet',
    'VNM': 'Công ty CP Sữa Việt Nam',
    'VPB': 'Ngân hàng TMCP Việt Nam Thịnh Vượng',
    'VRE': 'Công ty CP Vincom Retail'
}

# Alert types
ALERT_TYPES = {
    'price': 'Cảnh báo giá',
    'ma5': 'MA5',
    'ma10': 'MA10',
    'ma20': 'MA20',
    'ma50': 'MA50',
    'ma100': 'MA100',
    'bb_upper': 'Dải trên Bollinger',
    'bb_lower': 'Dải dưới Bollinger',
    'rsi': 'RSI',
    'macd': 'MACD',
    'volume_ma5': 'Khối lượng > TB 5 phiên',
    'volume_ma10': 'Khối lượng > TB 10 phiên',
    'volume_ma20': 'Khối lượng > TB 20 phiên'
}

def create_db_connection():
    """Create a connection to the database."""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_ADMIN_USER') or os.getenv('DB_USER'),
            password=os.getenv('DB_ADMIN_PASSWORD') or os.getenv('DB_PASSWORD'),
            port=os.getenv('DB_PORT')
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def execute_sql_in_thread(sql_query: str) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Execute SQL query and return results as a list of dictionaries.

    Args:
        sql_query (str): The SQL query to execute

    Returns:
        Tuple[List[Dict[str, Any]], bool]: A tuple containing:
            - List of dictionaries with query results or error message
            - Boolean indicating if an error occurred (True = error, False = success)
    """
    conn = None
    cur = None

    try:
        # Create database connection
        conn = create_db_connection()
        if not conn:
            return [{"error": "Could not connect to the database"}], True

        # Use RealDictCursor to automatically return results as dictionaries
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Execute the query
        cur.execute(sql_query)

        # Determine if this is a write operation (INSERT, UPDATE, DELETE)
        sql_upper = sql_query.strip().upper()
        is_write_operation = sql_upper.startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER'))

        # Check if it's a SELECT query (no description means no result set)
        if cur.description is None:
            # Not a SELECT query (INSERT, UPDATE, DELETE, etc.) without RETURNING
            conn.commit()
            return [{"message": "Query executed successfully", "rows_affected": cur.rowcount}], False

        # Fetch all results for SELECT queries or queries with RETURNING clause
        results = cur.fetchall()

        # IMPORTANT: Commit write operations even if they have RETURNING clause
        if is_write_operation:
            conn.commit()

        # Convert RealDictRow to regular dict
        results_list = [dict(row) for row in results]

        if not results_list:
            return [{"message": "No data found"}], False

        return results_list, False

    except psycopg2.Error as e:
        logger.error(f"Database error executing query: {e}")
        logger.error(f"Query was: {sql_query}")
        return [{"error": str(e), "query": sql_query}], True

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return [{"error": str(e)}], True

    finally:
        # Clean up
        if cur:
            cur.close()
        if conn:
            conn.close()
