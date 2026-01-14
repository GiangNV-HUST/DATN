"""
TCBS/VCI API Tools for MCP Server
Provides company info, financial data, and market data from TCBS/VCI sources
"""
import sys
import os
import logging

# ============================================================================
# CRITICAL: Suppress vnstock logging BEFORE import to prevent I/O errors
# vnstock library uses logger.info/error internally which fails in thread pools
# when stdout/stderr are closed. This must happen BEFORE importing vnstock.
# ============================================================================
class _SafeStreamHandler(logging.StreamHandler):
    """A StreamHandler that silently ignores I/O errors (for thread safety)"""
    def emit(self, record):
        try:
            super().emit(record)
        except (ValueError, OSError, IOError):
            pass

def _suppress_vnstock_logging():
    """Suppress all vnstock-related logging completely"""
    vnstock_loggers = [
        'vnstock', 'vnstock.explorer', 'vnstock.common', 'vnstock.core',
        'vnai', 'vnstock.explorer.vci', 'vnstock.explorer.tcbs', 'vnstock.quote',
        'vnstock.common.data', 'vnstock.common.client', 'vnstock.core.utils',
        'vnstock.core.utils.client', 'vnstock.explorer.tcbs.screener'
    ]
    for logger_name in vnstock_loggers:
        vnlogger = logging.getLogger(logger_name)
        vnlogger.setLevel(logging.CRITICAL + 100)  # Beyond CRITICAL
        vnlogger.propagate = False
        vnlogger.disabled = True
        vnlogger.handlers = []
        vnlogger.addHandler(logging.NullHandler())

def _install_safe_root_handler():
    """Replace root logger handlers with safe versions that ignore I/O errors"""
    root_logger = logging.getLogger()
    new_handlers = []
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, _SafeStreamHandler):
            safe_handler = _SafeStreamHandler(handler.stream)
            safe_handler.setLevel(handler.level)
            safe_handler.setFormatter(handler.formatter)
            new_handlers.append(safe_handler)
        else:
            new_handlers.append(handler)
    root_logger.handlers = new_handlers

# Suppress BEFORE import
_suppress_vnstock_logging()
_install_safe_root_handler()

# Suppress vnstock promo output (contains emojis that cause encoding errors on Windows)
# Must be done BEFORE importing vnstock
_original_stdout = sys.stdout
_original_stderr = sys.stderr
try:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    from vnstock import Vnstock
finally:
    sys.stdout.close()
    sys.stderr.close()
    sys.stdout = _original_stdout
    sys.stderr = _original_stderr

# Suppress again after import in case vnstock created new loggers during init
_suppress_vnstock_logging()
_install_safe_root_handler()

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd

from ..shared.database import execute_sql_in_thread

logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE HELPERS - DB-first strategy for faster response
# ============================================================================

def _serialize_db_value(val):
    """Convert database values to JSON-serializable format."""
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (datetime, )):
        return val.isoformat()
    if hasattr(val, 'isoformat'):  # date, datetime
        return val.isoformat()
    return val


def _get_company_overview_from_db(symbol: str) -> Optional[Dict]:
    """
    Get company overview from stock_screener table (instant).
    Maps screener fields to overview format.
    """
    sql = f"""
    SELECT
        ticker, exchange, short_name as company_name, industry_name, industry_code,
        close as price, volume, market_cap,
        pe as p_e, pb as p_b,
        roe, roa, eps,
        revenue_growth, profit_growth,
        free_float_rate, foreign_rate,
        created_at as last_updated
    FROM stock.stock_screener
    WHERE ticker = '{symbol.upper()}'
    LIMIT 1
    """
    records, is_error = execute_sql_in_thread(sql)

    if is_error or not records or (len(records) == 1 and 'message' in records[0]):
        return None

    row = records[0]
    return {k: _serialize_db_value(v) for k, v in row.items()}


def _get_financial_ratios_from_db(symbol: str, period: str = "quarter", num_periods: int = 8) -> Optional[List[Dict]]:
    """
    Get financial ratios from financial_ratios table (instant).
    """
    period_filter = "Q" if period == "quarter" else "Y"
    sql = f"""
    SELECT *
    FROM stock.financial_ratios
    WHERE ticker = '{symbol.upper()}'
    AND period_type = '{period_filter}'
    ORDER BY year DESC, quarter DESC
    LIMIT {num_periods}
    """
    records, is_error = execute_sql_in_thread(sql)

    if is_error or not records or (len(records) == 1 and 'message' in records[0]):
        return None

    return [{k: _serialize_db_value(v) for k, v in row.items()} for row in records]


def _get_income_statement_from_db(symbol: str, period: str = "quarter", num_periods: int = 4) -> Optional[List[Dict]]:
    """
    Get income statement from income_statement table (instant).
    """
    period_filter = "Q" if period == "quarter" else "Y"
    sql = f"""
    SELECT *
    FROM stock.income_statement
    WHERE ticker = '{symbol.upper()}'
    AND period_type = '{period_filter}'
    ORDER BY year DESC, quarter DESC
    LIMIT {num_periods}
    """
    records, is_error = execute_sql_in_thread(sql)

    if is_error or not records or (len(records) == 1 and 'message' in records[0]):
        return None

    return [{k: _serialize_db_value(v) for k, v in row.items()} for row in records]


def _get_balance_sheet_from_db(symbol: str, period: str = "quarter", num_periods: int = 4) -> Optional[List[Dict]]:
    """
    Get balance sheet from balance_sheet table (instant).
    """
    period_filter = "Q" if period == "quarter" else "Y"
    sql = f"""
    SELECT *
    FROM stock.balance_sheet
    WHERE ticker = '{symbol.upper()}'
    AND period_type = '{period_filter}'
    ORDER BY year DESC, quarter DESC
    LIMIT {num_periods}
    """
    records, is_error = execute_sql_in_thread(sql)

    if is_error or not records or (len(records) == 1 and 'message' in records[0]):
        return None

    return [{k: _serialize_db_value(v) for k, v in row.items()} for row in records]


def _get_cash_flow_from_db(symbol: str, period: str = "quarter", num_periods: int = 4) -> Optional[List[Dict]]:
    """
    Get cash flow from cash_flow table (instant).
    """
    period_filter = "Q" if period == "quarter" else "Y"
    sql = f"""
    SELECT *
    FROM stock.cash_flow
    WHERE ticker = '{symbol.upper()}'
    AND period_type = '{period_filter}'
    ORDER BY year DESC, quarter DESC
    LIMIT {num_periods}
    """
    records, is_error = execute_sql_in_thread(sql)

    if is_error or not records or (len(records) == 1 and 'message' in records[0]):
        return None

    return [{k: _serialize_db_value(v) for k, v in row.items()} for row in records]


def _get_price_history_from_db(symbol: str, start_date: str, end_date: str) -> Optional[List[Dict]]:
    """
    Get price history from stock_prices_1d table (instant).
    """
    sql = f"""
    SELECT time, ticker, open, high, low, close, volume,
           ma5, ma10, ma20, ma50, ma100,
           rsi, macd_main, macd_signal, macd_diff,
           bb_upper, bb_middle, bb_lower
    FROM stock.stock_prices_1d
    WHERE ticker = '{symbol.upper()}'
    AND time >= '{start_date}'
    AND time <= '{end_date}'
    ORDER BY time ASC
    """
    records, is_error = execute_sql_in_thread(sql)

    if is_error or not records or (len(records) == 1 and 'message' in records[0]):
        return None

    return [{k: _serialize_db_value(v) for k, v in row.items()} for row in records]


def _get_intraday_data_from_db(symbol: str) -> Optional[List[Dict]]:
    """
    Get intraday data from stock_prices_1m table (instant).
    Returns today's minute-level data.
    """
    sql = f"""
    SELECT time, ticker, open, high, low, close, volume
    FROM stock.stock_prices_1m
    WHERE ticker = '{symbol.upper()}'
    AND time >= CURRENT_DATE
    ORDER BY time ASC
    """
    records, is_error = execute_sql_in_thread(sql)

    if is_error or not records or (len(records) == 1 and 'message' in records[0]):
        return None

    return [{k: _serialize_db_value(v) for k, v in row.items()} for row in records]


def _safe_to_dict(df: pd.DataFrame) -> List[Dict]:
    """Safely convert DataFrame to list of dicts, handling NaN values"""
    if df is None or df.empty:
        return []
    # Replace NaN with None for JSON serialization
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient='records')


async def get_company_overview_mcp(symbol: str) -> Dict[str, Any]:
    """
    Get company overview information.
    Strategy: DATABASE first (instant) -> VCI API fallback

    Args:
        symbol: Stock symbol (e.g., VCB, FPT)

    Returns:
        Dict containing company overview data
    """
    # Try DATABASE first (instant response)
    db_data = _get_company_overview_from_db(symbol)
    if db_data:
        logger.info(f"[DB-first] Got company overview for {symbol} from database")
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "data": db_data,
            "source": "DATABASE"
        }

    # Fallback to VCI API
    logger.info(f"[DB-first] No DB data for {symbol}, falling back to VCI API")

    def _sync_fetch():
        try:
            stock = Vnstock().stock(symbol=symbol.upper(), source='VCI')
            overview = stock.company.overview()

            if overview is None or overview.empty:
                return {
                    "status": "error",
                    "message": f"No overview data found for {symbol}"
                }

            data = _safe_to_dict(overview)

            return {
                "status": "success",
                "symbol": symbol.upper(),
                "data": data[0] if data else {},
                "source": "VCI"
            }
        except Exception as e:
            logger.error(f"Error fetching company overview for {symbol}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "symbol": symbol.upper()
            }

    return await asyncio.to_thread(_sync_fetch)


async def get_company_profile_mcp(symbol: str) -> Dict[str, Any]:
    """
    Get detailed company profile from VCI

    Args:
        symbol: Stock symbol

    Returns:
        Dict containing company profile data
    """
    def _sync_fetch():
        try:
            stock = Vnstock().stock(symbol=symbol.upper(), source='VCI')
            profile = stock.company.profile()

            if profile is None or (hasattr(profile, 'empty') and profile.empty):
                return {
                    "status": "error",
                    "message": f"No profile data found for {symbol}"
                }

            # Handle different return types
            if isinstance(profile, pd.DataFrame):
                data = _safe_to_dict(profile)
                return {
                    "status": "success",
                    "symbol": symbol.upper(),
                    "data": data[0] if data else {},
                    "source": "VCI"
                }
            else:
                return {
                    "status": "success",
                    "symbol": symbol.upper(),
                    "data": profile if isinstance(profile, dict) else str(profile),
                    "source": "VCI"
                }
        except Exception as e:
            logger.error(f"Error fetching company profile for {symbol}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "symbol": symbol.upper()
            }

    return await asyncio.to_thread(_sync_fetch)


async def get_financial_ratios_mcp(
    symbol: str,
    period: str = "quarter",
    num_periods: int = 8
) -> Dict[str, Any]:
    """
    Get financial ratios.
    Strategy: DATABASE first (instant) -> VCI API fallback

    Args:
        symbol: Stock symbol
        period: 'quarter' or 'year'
        num_periods: Number of periods to fetch

    Returns:
        Dict containing financial ratios
    """
    # Try DATABASE first (instant response)
    db_data = _get_financial_ratios_from_db(symbol, period, num_periods)
    if db_data:
        logger.info(f"[DB-first] Got financial ratios for {symbol} from database")
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "period": period,
            "data": db_data,
            "count": len(db_data),
            "source": "DATABASE"
        }

    # Fallback to VCI API
    logger.info(f"[DB-first] No DB ratios for {symbol}, falling back to VCI API")

    def _sync_fetch():
        try:
            stock = Vnstock().stock(symbol=symbol.upper(), source='VCI')
            ratios = stock.finance.ratio(period=period)

            if ratios is None or ratios.empty:
                return {
                    "status": "error",
                    "message": f"No financial ratios found for {symbol}"
                }

            # Limit to requested periods
            ratios = ratios.head(num_periods)
            data = _safe_to_dict(ratios)

            return {
                "status": "success",
                "symbol": symbol.upper(),
                "period": period,
                "data": data,
                "count": len(data),
                "source": "VCI"
            }
        except Exception as e:
            logger.error(f"Error fetching financial ratios for {symbol}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "symbol": symbol.upper()
            }

    return await asyncio.to_thread(_sync_fetch)


async def get_income_statement_mcp(
    symbol: str,
    period: str = "quarter",
    num_periods: int = 4
) -> Dict[str, Any]:
    """
    Get income statement.
    Strategy: DATABASE first (instant) -> VCI API fallback

    Args:
        symbol: Stock symbol
        period: 'quarter' or 'year'
        num_periods: Number of periods to fetch

    Returns:
        Dict containing income statement data
    """
    # Try DATABASE first (instant response)
    db_data = _get_income_statement_from_db(symbol, period, num_periods)
    if db_data:
        logger.info(f"[DB-first] Got income statement for {symbol} from database")
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "period": period,
            "data": db_data,
            "count": len(db_data),
            "source": "DATABASE"
        }

    # Fallback to VCI API
    logger.info(f"[DB-first] No DB income statement for {symbol}, falling back to VCI API")

    def _sync_fetch():
        try:
            stock = Vnstock().stock(symbol=symbol.upper(), source='VCI')
            income = stock.finance.income_statement(period=period)

            if income is None or income.empty:
                return {
                    "status": "error",
                    "message": f"No income statement found for {symbol}"
                }

            income = income.head(num_periods)
            data = _safe_to_dict(income)

            return {
                "status": "success",
                "symbol": symbol.upper(),
                "period": period,
                "data": data,
                "count": len(data),
                "source": "VCI"
            }
        except Exception as e:
            logger.error(f"Error fetching income statement for {symbol}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "symbol": symbol.upper()
            }

    return await asyncio.to_thread(_sync_fetch)


async def get_balance_sheet_mcp(
    symbol: str,
    period: str = "quarter",
    num_periods: int = 4
) -> Dict[str, Any]:
    """
    Get balance sheet.
    Strategy: DATABASE first (instant) -> VCI API fallback

    Args:
        symbol: Stock symbol
        period: 'quarter' or 'year'
        num_periods: Number of periods to fetch

    Returns:
        Dict containing balance sheet data
    """
    # Try DATABASE first (instant response)
    db_data = _get_balance_sheet_from_db(symbol, period, num_periods)
    if db_data:
        logger.info(f"[DB-first] Got balance sheet for {symbol} from database")
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "period": period,
            "data": db_data,
            "count": len(db_data),
            "source": "DATABASE"
        }

    # Fallback to VCI API
    logger.info(f"[DB-first] No DB balance sheet for {symbol}, falling back to VCI API")

    def _sync_fetch():
        try:
            stock = Vnstock().stock(symbol=symbol.upper(), source='VCI')
            balance = stock.finance.balance_sheet(period=period)

            if balance is None or balance.empty:
                return {
                    "status": "error",
                    "message": f"No balance sheet found for {symbol}"
                }

            balance = balance.head(num_periods)
            data = _safe_to_dict(balance)

            return {
                "status": "success",
                "symbol": symbol.upper(),
                "period": period,
                "data": data,
                "count": len(data),
                "source": "VCI"
            }
        except Exception as e:
            logger.error(f"Error fetching balance sheet for {symbol}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "symbol": symbol.upper()
            }

    return await asyncio.to_thread(_sync_fetch)


async def get_cash_flow_mcp(
    symbol: str,
    period: str = "quarter",
    num_periods: int = 4
) -> Dict[str, Any]:
    """
    Get cash flow statement.
    Strategy: DATABASE first (instant) -> VCI API fallback

    Args:
        symbol: Stock symbol
        period: 'quarter' or 'year'
        num_periods: Number of periods to fetch

    Returns:
        Dict containing cash flow data
    """
    # Try DATABASE first (instant response)
    db_data = _get_cash_flow_from_db(symbol, period, num_periods)
    if db_data:
        logger.info(f"[DB-first] Got cash flow for {symbol} from database")
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "period": period,
            "data": db_data,
            "count": len(db_data),
            "source": "DATABASE"
        }

    # Fallback to VCI API
    logger.info(f"[DB-first] No DB cash flow for {symbol}, falling back to VCI API")

    def _sync_fetch():
        try:
            stock = Vnstock().stock(symbol=symbol.upper(), source='VCI')
            cashflow = stock.finance.cash_flow(period=period)

            if cashflow is None or cashflow.empty:
                return {
                    "status": "error",
                    "message": f"No cash flow data found for {symbol}"
                }

            cashflow = cashflow.head(num_periods)
            data = _safe_to_dict(cashflow)

            return {
                "status": "success",
                "symbol": symbol.upper(),
                "period": period,
                "data": data,
                "count": len(data),
                "source": "VCI"
            }
        except Exception as e:
            logger.error(f"Error fetching cash flow for {symbol}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "symbol": symbol.upper()
            }

    return await asyncio.to_thread(_sync_fetch)


async def get_price_history_mcp(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    lookback_days: int = 30
) -> Dict[str, Any]:
    """
    Get price history.
    Strategy: DATABASE first (instant) -> VCI API fallback

    Args:
        symbol: Stock symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        lookback_days: Days to look back if no start_date

    Returns:
        Dict containing price history
    """
    # Calculate dates
    if end_date:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_dt = datetime.now()

    if start_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_dt = end_dt - timedelta(days=lookback_days)

    start_date_str = start_dt.strftime('%Y-%m-%d')
    end_date_str = end_dt.strftime('%Y-%m-%d')

    # Try DATABASE first (instant response)
    db_data = _get_price_history_from_db(symbol, start_date_str, end_date_str)
    if db_data:
        logger.info(f"[DB-first] Got price history for {symbol} from database ({len(db_data)} records)")
        latest = db_data[-1] if db_data else None
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "start_date": start_date_str,
            "end_date": end_date_str,
            "data": db_data,
            "latest": latest,
            "count": len(db_data),
            "source": "DATABASE"
        }

    # Fallback to VCI API
    logger.info(f"[DB-first] No DB price history for {symbol}, falling back to VCI API")

    def _sync_fetch():
        try:
            stock = Vnstock().stock(symbol=symbol.upper(), source='VCI')

            history = stock.quote.history(
                start=start_date_str,
                end=end_date_str
            )

            if history is None or history.empty:
                return {
                    "status": "error",
                    "message": f"No price history found for {symbol}"
                }

            data = _safe_to_dict(history)

            # Get latest data
            latest = data[-1] if data else None

            return {
                "status": "success",
                "symbol": symbol.upper(),
                "start_date": start_date_str,
                "end_date": end_date_str,
                "data": data,
                "latest": latest,
                "count": len(data),
                "source": "VCI"
            }
        except Exception as e:
            logger.error(f"Error fetching price history for {symbol}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "symbol": symbol.upper()
            }

    return await asyncio.to_thread(_sync_fetch)


async def get_intraday_data_mcp(symbol: str) -> Dict[str, Any]:
    """
    Get intraday trading data.
    Strategy: DATABASE first (instant) -> VCI API fallback

    Args:
        symbol: Stock symbol

    Returns:
        Dict containing intraday data
    """
    # Try DATABASE first (instant response)
    db_data = _get_intraday_data_from_db(symbol)
    if db_data:
        logger.info(f"[DB-first] Got intraday data for {symbol} from database ({len(db_data)} records)")
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "data": db_data,
            "count": len(db_data),
            "source": "DATABASE"
        }

    # Fallback to VCI API
    logger.info(f"[DB-first] No DB intraday data for {symbol}, falling back to VCI API")

    def _sync_fetch():
        try:
            stock = Vnstock().stock(symbol=symbol.upper(), source='VCI')
            intraday = stock.quote.intraday()

            if intraday is None or intraday.empty:
                return {
                    "status": "error",
                    "message": f"No intraday data found for {symbol}"
                }

            data = _safe_to_dict(intraday)

            return {
                "status": "success",
                "symbol": symbol.upper(),
                "data": data,
                "count": len(data),
                "source": "VCI"
            }
        except Exception as e:
            logger.error(f"Error fetching intraday data for {symbol}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "symbol": symbol.upper()
            }

    return await asyncio.to_thread(_sync_fetch)


async def get_all_symbols_mcp(exchange: str = "all") -> Dict[str, Any]:
    """
    Get list of all stock symbols

    Args:
        exchange: Filter by exchange ('HOSE', 'HNX', 'UPCOM', 'all')

    Returns:
        Dict containing list of symbols
    """
    def _sync_fetch():
        try:
            stock = Vnstock().stock(source='VCI')

            # Get symbols for each exchange
            symbols_data = []

            exchanges = ['HOSE', 'HNX', 'UPCOM'] if exchange == 'all' else [exchange.upper()]

            for exch in exchanges:
                try:
                    symbols = stock.listing.symbols_by_exchange(exchange=exch)
                    if symbols is not None:
                        for sym in symbols:
                            symbols_data.append({
                                "symbol": sym,
                                "exchange": exch
                            })
                except Exception as e:
                    logger.warning(f"Error fetching symbols for {exch}: {e}")

            return {
                "status": "success",
                "exchange_filter": exchange,
                "symbols": symbols_data,
                "count": len(symbols_data),
                "source": "VCI"
            }
        except Exception as e:
            logger.error(f"Error fetching symbols: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    return await asyncio.to_thread(_sync_fetch)


async def get_stock_full_info_mcp(symbol: str) -> Dict[str, Any]:
    """
    Get comprehensive stock information combining multiple data sources

    Args:
        symbol: Stock symbol

    Returns:
        Dict containing comprehensive stock info
    """
    # Fetch all data concurrently
    results = await asyncio.gather(
        get_company_overview_mcp(symbol),
        get_financial_ratios_mcp(symbol, period="quarter", num_periods=4),
        get_price_history_mcp(symbol, lookback_days=30),
        return_exceptions=True
    )

    overview_result = results[0] if not isinstance(results[0], Exception) else {"status": "error", "message": str(results[0])}
    ratios_result = results[1] if not isinstance(results[1], Exception) else {"status": "error", "message": str(results[1])}
    price_result = results[2] if not isinstance(results[2], Exception) else {"status": "error", "message": str(results[2])}

    # Combine results
    combined = {
        "status": "success",
        "symbol": symbol.upper(),
        "overview": overview_result.get("data", {}) if overview_result.get("status") == "success" else None,
        "financial_ratios": ratios_result.get("data", []) if ratios_result.get("status") == "success" else None,
        "price_history": {
            "latest": price_result.get("latest"),
            "data_count": price_result.get("count", 0)
        } if price_result.get("status") == "success" else None,
        "errors": []
    }

    # Collect any errors
    if overview_result.get("status") != "success":
        combined["errors"].append(f"Overview: {overview_result.get('message')}")
    if ratios_result.get("status") != "success":
        combined["errors"].append(f"Ratios: {ratios_result.get('message')}")
    if price_result.get("status") != "success":
        combined["errors"].append(f"Price: {price_result.get('message')}")

    if combined["errors"]:
        combined["status"] = "partial_success" if any([combined["overview"], combined["financial_ratios"], combined["price_history"]]) else "error"

    return combined


# Export all tools
__all__ = [
    'get_company_overview_mcp',
    'get_company_profile_mcp',
    'get_financial_ratios_mcp',
    'get_income_statement_mcp',
    'get_balance_sheet_mcp',
    'get_cash_flow_mcp',
    'get_price_history_mcp',
    'get_intraday_data_mcp',
    'get_all_symbols_mcp',
    'get_stock_full_info_mcp'
]
