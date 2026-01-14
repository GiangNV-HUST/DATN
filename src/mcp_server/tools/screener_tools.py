"""
Stock screener tools for MCP server
Provides stock filtering with technical indicators and fundamentals

Data Source Strategy:
- PRIMARY: Database (stock_screener table) - has price, volume, RSI, MA, PE, ROE, etc.
- NOTE: TCBS screener API is currently returning 404 errors (as of Jan 2026)
- Data is populated via Kafka pipeline from VnStock API
"""
import asyncio
import operator
import logging
from typing import Dict, List, Tuple, Optional, Union, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Define operators dictionary
ops = {
    '>': operator.gt,
    '<': operator.lt,
    '>=': operator.ge,
    '<=': operator.le,
    '==': operator.eq,
    '!=': operator.ne
}

# Define columns that are object type (strings)
string_columns = [
    'ticker', 'exchange', 'industry', 'price_vs_sma5', 'price_vs_sma10',
    'price_vs_sma20', 'price_vs_sma50', 'price_vs_sma100', 'macd_histogram',
    'rsi14_status', 'foreign_transaction', 'uptrend', 'tcbs_recommend',
    'tcbs_buy_sell_signal', 'bolling_band_signal', 'price_break_out52_week',
    'price_wash_out52_week', 'has_financial_report'
]


def parse_condition(cond_str: str, column: str) -> Tuple[callable, Any]:
    """
    Parse a condition string like '>15' into an operator function and value

    Args:
        cond_str: String condition (e.g., '>15', '==Ngân hàng', 'contains:Ngân hàng')
        column: Column name to determine if we should parse as string or float

    Returns:
        Tuple of (operator function, value)
    """
    # Handle special 'contains:' prefix for string contains matching
    if cond_str.startswith('contains:'):
        value_str = cond_str[9:]  # Remove 'contains:' prefix
        # Return a lambda that does case-insensitive contains check
        return lambda col, val: col.str.lower().str.contains(val.lower(), na=False), value_str

    for op_str in ['>=', '<=', '==', '!=', '>', '<']:
        if cond_str.startswith(op_str):
            value_str = cond_str[len(op_str):]

            # For string columns, keep the value as string
            if column in string_columns:
                return ops[op_str], value_str

            # For numeric columns, convert to float
            return ops[op_str], float(value_str)

    raise ValueError(f"Invalid condition: {cond_str}")


def apply_filters(df: pd.DataFrame, conditions: Dict[str, str]) -> pd.DataFrame:
    """Apply filtering conditions to the dataframe"""
    if df.empty:
        return df

    filtered_df = df.copy()

    # Apply each condition
    for column, cond in conditions.items():
        if column not in filtered_df.columns:
            logger.warning(f"Column '{column}' not found in dataframe. Skipping this condition.")
            continue

        try:
            op_func, value = parse_condition(cond, column)
            # Remove NaN values to avoid errors
            filtered_df = filtered_df[filtered_df[column].notna()]
            # Apply the condition
            filtered_df = filtered_df[op_func(filtered_df[column], value)]
            logger.info(f"Applied filter {column} {cond}: {len(filtered_df)} stocks remaining")
        except Exception as e:
            logger.error(f"Error applying condition {column} {cond}: {e}")

    return filtered_df


def sort_results(df: pd.DataFrame, sort_by: str = "avg_trading_value_20d", ascending: bool = False) -> pd.DataFrame:
    """Sort the filtered results"""
    if df.empty:
        return df

    if sort_by not in df.columns:
        logger.warning(f"Sort column '{sort_by}' not found. Using default 'avg_trading_value_20d'")
        sort_by = "avg_trading_value_20d"

    try:
        return df.sort_values(by=sort_by, ascending=ascending)
    except Exception as e:
        logger.error(f"Error sorting by {sort_by}: {e}")
        return df


def screen_stocks_from_database(
    conditions: Dict[str, str],
    sort_by: str = "avg_trading_value_20d",
    ascending: bool = False,
    limit: int = 20
) -> pd.DataFrame:
    """
    Screen stocks from database when TCBS API is unavailable

    Args:
        conditions: Dictionary of column:condition pairs
        sort_by: Column to sort results by
        ascending: Sort order
        limit: Maximum number of results

    Returns:
        DataFrame of filtered stocks from database
    """
    try:
        from ..shared.database import execute_sql_in_thread

        # Get stock data from stock_screener table (imported from vnstock)
        sql_query = """
        SELECT
            ticker,
            exchange,
            industry,
            close,
            open,
            high,
            low,
            volume,
            change_percent_1d,
            market_cap,
            pe,
            pb,
            roe,
            eps,
            dividend_yield,
            rsi14,
            ma5,
            ma10,
            ma20,
            ma50,
            avg_trading_value_20d,
            updated_at
        FROM stock.stock_screener
        WHERE updated_at >= CURRENT_DATE - INTERVAL '7 days'
        ORDER BY avg_trading_value_20d DESC NULLS LAST
        LIMIT 500;
        """

        records, is_error = execute_sql_in_thread(sql_query)

        if is_error:
            logger.error(f"Database error: {records}")
            return pd.DataFrame()

        # Convert to DataFrame
        data = []
        for record in records:
            if isinstance(record, dict) and 'message' not in record:
                data.append(record)

        if not data:
            logger.warning("No data in stock_screener table")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        logger.info(f"Loaded {len(df)} stocks from database")

        # Apply filters
        filtered_df = apply_filters(df, conditions)

        # Sort results
        sorted_df = sort_results(filtered_df, sort_by, ascending)

        return sorted_df.head(limit)

    except Exception as e:
        logger.error(f"Error in screen_stocks_from_database: {str(e)}")
        return pd.DataFrame()


def screen_stocks_sync(
    conditions: Dict[str, str],
    sort_by: str = "avg_trading_value_20d",
    ascending: bool = False,
    limit: int = 20
) -> pd.DataFrame:
    """
    Screen stocks based on given conditions (synchronous version)
    Uses database as primary source (TCBS API is currently unavailable - 404 error)

    Args:
        conditions: Dictionary of column:condition pairs (e.g. {'roe': '>15', 'pe': '<15'})
        sort_by: Column to sort results by
        ascending: Sort order
        limit: Maximum number of results to return

    Returns:
        DataFrame of filtered stocks
    """
    # Use database directly (TCBS screener API returns 404 as of Jan 2026)
    logger.info("Using database for stock screening")
    return screen_stocks_from_database(conditions, sort_by, ascending, limit)


async def screen_stocks_mcp(
    conditions: Dict[str, str] = None,
    sort_by: str = "avg_trading_value_20d",
    ascending: bool = False,
    limit: int = 20
) -> Dict[str, Any]:
    """
    MCP version of screen_stocks - async wrapper

    Args:
        conditions: Dictionary of column:condition pairs (e.g. {'roe': '>15', 'pe': '<15'}).
                   If None or empty, returns top stocks by trading value.
        sort_by: Column to sort results by (default: "avg_trading_value_20d")
        ascending: Sort order (default: False - descending)
        limit: Maximum number of results (default: 20)

    Returns:
        Dictionary containing:
        - status: "success", "error", or "no_results"
        - result_count: Number of stocks found
        - data: List of dictionaries, each representing a stock
        - conditions: The conditions that were applied
        - sort_by: The column used for sorting
    """
    # Default to empty conditions if None
    if conditions is None:
        conditions = {}
    try:
        # Run synchronous screener in thread pool
        result_df = await asyncio.to_thread(
            screen_stocks_sync,
            conditions,
            sort_by,
            ascending,
            limit
        )

        # Check if results are empty
        if result_df.empty:
            return {
                "status": "no_results",
                "result_count": 0,
                "data": [],
                "conditions": conditions,
                "sort_by": sort_by,
                "message": "No stocks match the given conditions"
            }

        # Get relevant columns to keep (ticker, company name, filter columns, sort column)
        columns_to_keep = ['ticker', 'exchange', 'industry']

        # Add filter columns
        for column in conditions.keys():
            if column not in columns_to_keep and column in result_df.columns:
                columns_to_keep.append(column)

        # Add sort column if not already included
        if sort_by not in columns_to_keep and sort_by in result_df.columns:
            columns_to_keep.append(sort_by)

        # Add some commonly useful columns
        useful_columns = ['close', 'change_percent_1d', 'avg_trading_value_20d', 'market_cap']
        for col in useful_columns:
            if col not in columns_to_keep and col in result_df.columns:
                columns_to_keep.append(col)

        # Keep only the relevant columns
        result_df = result_df[[col for col in columns_to_keep if col in result_df.columns]]

        # Replace NaN values with None before converting to dictionary
        result_df = result_df.replace({np.nan: None})

        # Convert DataFrame to list of dictionaries
        result_data = result_df.to_dict(orient='records')

        # Return the results
        return {
            "status": "success",
            "result_count": len(result_data),
            "data": result_data,
            "conditions": conditions,
            "sort_by": sort_by,
            "message": f"Found {len(result_data)} stocks matching the conditions"
        }

    except Exception as e:
        logger.error(f"Error in screen_stocks_mcp: {str(e)}")
        return {
            "status": "error",
            "result_count": 0,
            "data": [],
            "conditions": conditions,
            "sort_by": sort_by,
            "message": f"Error screening stocks: {str(e)}"
        }


async def get_screener_columns_mcp() -> Dict[str, Any]:
    """
    Get list of available columns for stock screening

    Returns:
        Dictionary with available columns and their descriptions
    """
    columns_info = {
        "status": "success",
        "columns": {
            "technical": {
                "close": "Current price",
                "change_percent_1d": "1-day price change %",
                "price_vs_sma5": "Price vs 5-day MA",
                "price_vs_sma10": "Price vs 10-day MA",
                "price_vs_sma20": "Price vs 20-day MA",
                "price_vs_sma50": "Price vs 50-day MA",
                "price_vs_sma100": "Price vs 100-day MA",
                "rsi14": "RSI 14-day",
                "rsi14_status": "RSI status",
                "macd": "MACD",
                "macd_histogram": "MACD histogram",
                "bb_upper": "Bollinger Bands upper",
                "bb_lower": "Bollinger Bands lower",
                "bolling_band_signal": "Bollinger signal",
                "volume": "Trading volume",
                "avg_trading_value_20d": "Avg trading value 20 days"
            },
            "fundamental": {
                "pe": "P/E ratio",
                "pb": "P/B ratio",
                "roe": "Return on Equity %",
                "roa": "Return on Assets %",
                "eps": "Earnings per share",
                "revenue_growth": "Revenue growth %",
                "profit_growth": "Profit growth %",
                "market_cap": "Market capitalization"
            },
            "general": {
                "ticker": "Stock symbol",
                "exchange": "Exchange (HOSE/HNX/UPCOM)",
                "industry": "Industry sector"
            }
        },
        "operators": [">", "<", ">=", "<=", "==", "!="],
        "example_conditions": {
            "roe": ">15",
            "pe": "<15",
            "rsi14": ">70",
            "market_cap": ">1000000000000"
        }
    }

    return columns_info
