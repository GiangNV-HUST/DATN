"""
Financial data tools for MCP server
Provides access to balance sheet, income statement, cash flow, and financial ratios

Strategy: DATABASE FIRST (instant) -> VCI API fallback
- Database is the PRIMARY source (instant response, ~50ms)
- API is used as FALLBACK when DB has no data
- Financial data updates quarterly, so DB cache is highly effective
"""
import asyncio
import datetime
import logging
from typing import Optional, List, Dict, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)

# Suppress vnstock logging to prevent "I/O operation on closed file" errors in thread pools
for _vn_logger_name in ['vnstock', 'vnstock.explorer', 'vnstock.common', 'vnstock.core',
                         'vnai', 'vnstock.explorer.vci', 'vnstock.explorer.tcbs', 'vnstock.quote']:
    _vn_logger = logging.getLogger(_vn_logger_name)
    _vn_logger.setLevel(logging.CRITICAL)
    _vn_logger.propagate = False
    if not _vn_logger.handlers:
        _vn_logger.addHandler(logging.NullHandler())


def serialize_val(val):
    """Convert database values to JSON-serializable format."""
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    return val


async def _fetch_from_api(ticker: str, data_type: str, period: str, num_periods: int) -> Dict:
    """
    Fetch financial data from VCI API (FALLBACK SOURCE)

    Args:
        ticker: Stock symbol
        data_type: 'balance_sheet', 'income_statement', 'cash_flow', 'ratio'
        period: 'quarter' or 'year'
        num_periods: Number of periods to fetch

    Returns:
        Dict with status and data
    """
    def _sync_fetch():
        try:
            from vnstock import Vnstock
            import pandas as pd

            stock = Vnstock().stock(symbol=ticker.upper(), source='VCI')

            # Map data_type to VCI method
            if data_type == 'balance_sheet':
                df = stock.finance.balance_sheet(period=period)
            elif data_type == 'income_statement':
                df = stock.finance.income_statement(period=period)
            elif data_type == 'cash_flow':
                df = stock.finance.cash_flow(period=period)
            elif data_type == 'ratio':
                df = stock.finance.ratio(period=period)
            else:
                return {"status": "error", "message": f"Unknown data_type: {data_type}"}

            if df is None or df.empty:
                return {"status": "error", "message": f"No {data_type} data from API for {ticker}"}

            # Limit to requested periods
            df = df.head(num_periods)

            # Convert to dict, handling NaN and MultiIndex columns
            df = df.where(pd.notnull(df), None)

            # Handle MultiIndex columns (convert tuple to string)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = ['_'.join(map(str, col)).strip() for col in df.columns]
            else:
                # Ensure all column names are strings
                df.columns = [str(col) if not isinstance(col, str) else col for col in df.columns]

            data = df.to_dict(orient='records')

            return {
                "status": "success",
                "ticker": ticker.upper(),
                "data_type": data_type,
                "period": period,
                "data": data,
                "count": len(data),
                "source": "API"
            }

        except Exception as e:
            logger.warning(f"API fetch failed for {ticker}/{data_type}: {e}")
            return {"status": "error", "message": str(e)}

    return await asyncio.to_thread(_sync_fetch)


async def _fetch_from_database(ticker: str, data_type: str, period: str, num_periods: int) -> Dict:
    """
    Fetch financial data from Database (PRIMARY SOURCE - instant response)

    Args:
        ticker: Stock symbol
        data_type: 'balance_sheet', 'income_statement', 'cash_flow', 'ratio'
        period: 'quarterly' or 'yearly'
        num_periods: Number of periods to fetch

    Returns:
        Dict with status and data
    """
    def _sync_fetch():
        try:
            from ..shared.database import execute_sql_in_thread

            # Map data_type to table name
            table_map = {
                'balance_sheet': 'stock.balance_sheet',
                'income_statement': 'stock.income_statement',
                'cash_flow': 'stock.cash_flow',
                'ratio': 'stock.financial_ratios'
            }

            table_name = table_map.get(data_type)
            if not table_name:
                return {"status": "error", "message": f"Unknown data_type: {data_type}"}

            # Build query
            sql_query = f"""
            SELECT * FROM {table_name}
            WHERE ticker = '{ticker.upper()}'
            ORDER BY year DESC, quarter DESC
            LIMIT {num_periods}
            """

            records, is_error = execute_sql_in_thread(sql_query)

            if is_error:
                return {"status": "error", "message": records[0].get("error", "Database error")}

            # Process records
            data = []
            for record in records:
                if isinstance(record, dict) and 'message' not in record:
                    serialized = {k: serialize_val(v) for k, v in record.items()}
                    data.append(serialized)

            if not data:
                return {"status": "error", "message": f"No {data_type} data in database for {ticker}"}

            return {
                "status": "success",
                "ticker": ticker.upper(),
                "data_type": data_type,
                "period": period,
                "data": data,
                "count": len(data),
                "source": "DATABASE"
            }

        except Exception as e:
            logger.error(f"Database fetch failed for {ticker}/{data_type}: {e}")
            return {"status": "error", "message": str(e)}

    return await asyncio.to_thread(_sync_fetch)


async def _get_financial_data_for_ticker(
    ticker: str,
    data_type: str,
    period: str,
    num_periods: int
) -> Dict:
    """
    Get financial data for a single ticker
    Strategy: DATABASE first (instant) -> API fallback

    Args:
        ticker: Stock symbol
        data_type: Type of financial data
        period: 'quarter' or 'year'
        num_periods: Number of periods

    Returns:
        Dict with financial data
    """
    # Try DATABASE first (PRIMARY - instant response)
    db_result = await _fetch_from_database(ticker, data_type, period, num_periods)

    if db_result.get("status") == "success":
        logger.info(f"[DB-first] Got {data_type} for {ticker} from Database (instant)")
        return db_result

    # Fallback to API (slower but has latest data)
    logger.info(f"[DB-first] No DB data for {ticker}/{data_type}, falling back to API")
    api_result = await _fetch_from_api(ticker, data_type, period, num_periods)

    if api_result.get("status") == "success":
        logger.info(f"[DB-first] Got {data_type} for {ticker} from API (fallback)")
        return api_result

    # Both failed
    return {
        "status": "error",
        "ticker": ticker.upper(),
        "data_type": data_type,
        "message": f"Failed to fetch {data_type} from both Database and API",
        "db_error": db_result.get("message"),
        "api_error": api_result.get("message")
    }


async def get_financial_data_mcp(
    tickers: List[str],
    is_balance_sheet: bool = False,
    is_income_statement: bool = False,
    is_cash_flow: bool = False,
    is_financial_ratios: bool = False,
    period: str = "quarterly",
    num_periods: int = 4
) -> Dict:
    """
    Get financial data for multiple tickers

    Data Source Strategy: DATABASE FIRST (instant) -> API fallback
    1. PRIMARY: Database (instant response ~50ms)
    2. FALLBACK: VCI API (when DB has no data, ~7s per call)

    Args:
        tickers: List of stock symbols
        is_balance_sheet: Fetch balance sheet
        is_income_statement: Fetch income statement
        is_cash_flow: Fetch cash flow
        is_financial_ratios: Fetch financial ratios
        period: "quarterly" or "yearly"
        num_periods: Number of periods (default: 4)

    Returns:
        Dictionary containing financial data
    """
    # Determine which data types to fetch
    data_types = []
    if is_balance_sheet:
        data_types.append("balance_sheet")
    if is_income_statement:
        data_types.append("income_statement")
    if is_cash_flow:
        data_types.append("cash_flow")
    if is_financial_ratios:
        data_types.append("ratio")

    if not data_types:
        return {
            "status": "error",
            "message": "No financial data type selected. Set at least one flag to True."
        }

    # Convert period format
    api_period = "quarter" if period == "quarterly" else "year"

    # Create tasks for all ticker/data_type combinations
    tasks = []
    for ticker in tickers:
        for data_type in data_types:
            task = _get_financial_data_for_ticker(ticker, data_type, api_period, num_periods)
            tasks.append((ticker, data_type, task))

    # Execute all tasks concurrently
    results = {}
    errors = []

    for ticker, data_type, task in tasks:
        result = await task

        if ticker not in results:
            results[ticker] = {}

        results[ticker][data_type] = result

        if result.get("status") != "success":
            errors.append(f"{ticker}/{data_type}: {result.get('message')}")

    # Determine overall status
    if len(errors) == len(tasks):
        status = "error"
        message = "Failed to fetch all requested data"
    elif errors:
        status = "partial_success"
        message = f"Fetched data with {len(errors)} error(s)"
    else:
        status = "success"
        message = f"Successfully fetched financial data for {len(tickers)} ticker(s)"

    return {
        "status": status,
        "results": results,
        "period": period,
        "num_periods": num_periods,
        "message": message,
        "errors": errors if errors else None
    }
