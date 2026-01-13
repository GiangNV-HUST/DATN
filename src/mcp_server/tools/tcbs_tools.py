"""
TCBS/VCI API Tools for MCP Server
Provides company info, financial data, and market data from TCBS/VCI sources
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
from vnstock import Vnstock

logger = logging.getLogger(__name__)


def _safe_to_dict(df: pd.DataFrame) -> List[Dict]:
    """Safely convert DataFrame to list of dicts, handling NaN values"""
    if df is None or df.empty:
        return []
    # Replace NaN with None for JSON serialization
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient='records')


async def get_company_overview_mcp(symbol: str) -> Dict[str, Any]:
    """
    Get company overview information from VCI

    Args:
        symbol: Stock symbol (e.g., VCB, FPT)

    Returns:
        Dict containing company overview data
    """
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
    Get financial ratios from VCI

    Args:
        symbol: Stock symbol
        period: 'quarter' or 'year'
        num_periods: Number of periods to fetch

    Returns:
        Dict containing financial ratios
    """
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
    Get income statement from VCI

    Args:
        symbol: Stock symbol
        period: 'quarter' or 'year'
        num_periods: Number of periods to fetch

    Returns:
        Dict containing income statement data
    """
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
    Get balance sheet from VCI

    Args:
        symbol: Stock symbol
        period: 'quarter' or 'year'
        num_periods: Number of periods to fetch

    Returns:
        Dict containing balance sheet data
    """
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
    Get cash flow statement from VCI

    Args:
        symbol: Stock symbol
        period: 'quarter' or 'year'
        num_periods: Number of periods to fetch

    Returns:
        Dict containing cash flow data
    """
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
    Get price history from VCI

    Args:
        symbol: Stock symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        lookback_days: Days to look back if no start_date

    Returns:
        Dict containing price history
    """
    def _sync_fetch():
        try:
            stock = Vnstock().stock(symbol=symbol.upper(), source='VCI')

            # Calculate dates
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            else:
                end_dt = datetime.now()

            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            else:
                start_dt = end_dt - timedelta(days=lookback_days)

            history = stock.quote.history(
                start=start_dt.strftime('%Y-%m-%d'),
                end=end_dt.strftime('%Y-%m-%d')
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
                "start_date": start_dt.strftime('%Y-%m-%d'),
                "end_date": end_dt.strftime('%Y-%m-%d'),
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
    Get intraday trading data from VCI

    Args:
        symbol: Stock symbol

    Returns:
        Dict containing intraday data
    """
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
