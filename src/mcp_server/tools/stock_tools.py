"""
Stock data tools for MCP server
Async wrappers around existing stock tools

Performance optimized:
- FastChartGenerator: Sử dụng template caching để vẽ chart nhanh hơn
  + Lần đầu: ~1.5s (tạo template)
  + Các lần sau: ~0.3-0.5s (chỉ update data)
"""
import asyncio
import datetime
import logging
import tempfile
import os
from typing import Optional, List, Dict
from decimal import Decimal
import concurrent.futures

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import mplfinance as mpf

from ..shared.database import execute_sql_in_thread
from .chart_generator import get_chart_generator, generate_fast_chart

logger = logging.getLogger(__name__)


def serialize_val(val):
    """Convert database values to JSON-serializable format."""
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    return val


async def _get_single_stock_data(symbol: str, table_name: str, start_date_str: str, end_date_str: str) -> dict:
    """
    Helper function to fetch data for a single stock symbol (async).
    """
    def _sync_fetch():
        try:
            sql_query = f"""
            SELECT * FROM {table_name}
            WHERE ticker = '{symbol}'
            AND time >= '{start_date_str}'
            AND time <= '{end_date_str}'
            ORDER BY time ASC
            """

            records, is_error = execute_sql_in_thread(sql_query)

            if is_error:
                raise Exception(records[0].get("error", "Unknown database error"))

            data = []
            for record in records:
                if isinstance(record, dict) and 'message' in record:
                    continue
                serialized_record = {k: serialize_val(v) for k, v in record.items()}
                data.append(serialized_record)

            latest = data[-1] if data else None

            result = {
                'symbol': symbol,
                'start': start_date_str,
                'end': end_date_str,
                'data': data,
                'latest': latest,
            }

            return {"status": "success", "result": result}

        except Exception as e:
            logger.error(f"Error fetching stock data for {symbol}: {e}")
            error_result = {
                'symbol': symbol,
                'start': start_date_str,
                'end': end_date_str,
                'data': [],
                'latest': None,
                'error': str(e)
            }
            return {"status": "error", "message": str(e), "result": error_result}

    # Run synchronous function in thread pool
    return await asyncio.to_thread(_sync_fetch)


async def _get_realtime_price_from_db(symbol: str) -> dict:
    """
    Get realtime price from database (stock_prices_1m table).
    Data is collected every minute by Airflow DAG.
    """
    def _sync_fetch_from_db():
        try:
            # Query the latest minute data from database
            sql_query = f"""
            SELECT time, ticker, open, high, low, close, volume
            FROM stock.stock_prices_1m
            WHERE ticker = '{symbol.upper()}'
            ORDER BY time DESC
            LIMIT 1
            """

            records, is_error = execute_sql_in_thread(sql_query)

            if is_error:
                return {"status": "error", "message": records[0].get("error", "Database error")}

            if records and len(records) > 0 and 'message' not in records[0]:
                record = records[0]
                return {
                    "status": "success",
                    "symbol": symbol.upper(),
                    "price": float(record.get('close', 0)) * 1000,  # Convert to VND
                    "open": float(record.get('open', 0)) * 1000,
                    "high": float(record.get('high', 0)) * 1000,
                    "low": float(record.get('low', 0)) * 1000,
                    "volume": int(record.get('volume', 0)),
                    "time": str(record.get('time', '')),
                    "source": "DATABASE_1M",
                    "is_realtime": True
                }
            else:
                return {"status": "error", "message": "No minute data in database"}

        except Exception as e:
            logger.warning(f"Database fetch failed for {symbol}: {e}")
            return {"status": "error", "message": str(e)}

    return await asyncio.to_thread(_sync_fetch_from_db)


async def _get_realtime_price_from_api(symbol: str) -> dict:
    """
    Get realtime/intraday price for a stock using VCI API.
    Fallback when database doesn't have recent data.
    """
    def _sync_fetch_realtime():
        try:
            from vnstock import Vnstock

            stock = Vnstock().stock(symbol=symbol.upper(), source='VCI')

            # Get intraday data (most recent)
            intraday = stock.quote.intraday()

            if intraday is not None and not intraday.empty:
                latest = intraday.iloc[-1].to_dict()

                # Get additional info from history for today
                today = datetime.datetime.now().strftime('%Y-%m-%d')
                history = stock.quote.history(start=today, end=today)

                daily_info = {}
                if history is not None and not history.empty:
                    daily_info = history.iloc[-1].to_dict()

                return {
                    "status": "success",
                    "symbol": symbol.upper(),
                    "price": latest.get('price') or latest.get('close'),
                    "volume": latest.get('volume', 0),
                    "time": str(latest.get('time', '')),
                    "change": daily_info.get('change', 0),
                    "change_pct": daily_info.get('change_percent', 0),
                    "open": daily_info.get('open'),
                    "high": daily_info.get('high'),
                    "low": daily_info.get('low'),
                    "source": "VCI_INTRADAY",
                    "is_realtime": True
                }
            else:
                return {"status": "error", "message": "No intraday data available"}

        except Exception as e:
            logger.warning(f"Realtime fetch failed for {symbol}: {e}")
            return {"status": "error", "message": str(e)}

    return await asyncio.to_thread(_sync_fetch_realtime)


async def _get_realtime_price(symbol: str) -> dict:
    """
    Get realtime price - tries database first, then API fallback.

    Priority:
    1. Database (stock_prices_1m) - Data collected every minute by Airflow
    2. VCI API - Fallback if database data is stale or unavailable
    """
    # Try database first
    db_result = await _get_realtime_price_from_db(symbol)

    if db_result.get("status") == "success":
        # Check if data is recent (within last 5 minutes)
        try:
            data_time = datetime.datetime.fromisoformat(str(db_result.get("time", "")))
            now = datetime.datetime.now()
            age_minutes = (now - data_time).total_seconds() / 60

            if age_minutes <= 5:
                logger.info(f"Using database data for {symbol} (age: {age_minutes:.1f} min)")
                return db_result
            else:
                logger.info(f"Database data stale for {symbol} (age: {age_minutes:.1f} min), trying API")
        except:
            pass

    # Fallback to API
    logger.info(f"Fetching {symbol} from VCI API")
    return await _get_realtime_price_from_api(symbol)


async def get_stock_data_mcp(
    symbols: list[str],
    interval: str = '1D',
    lookback_days: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    realtime: bool = True
) -> dict:
    """
    MCP version of get_stock_data - fetches stock data for multiple symbols.

    By default, tries to get realtime/intraday data first for current prices,
    then falls back to daily data if needed.

    Args:
        symbols: List of stock symbols
        interval: Time interval (default: '1D')
        lookback_days: Number of days to look back
        start_date: Start date in format 'YYYY-MM-DD'
        end_date: End date in format 'YYYY-MM-DD'
        realtime: If True, try to get realtime price first (default: True)

    Returns:
        dict: Dictionary containing status and results
    """
    results = {}
    errors = []

    # If realtime is requested and lookback is small (or not specified), try realtime first
    try_realtime = realtime and (lookback_days is None or lookback_days <= 1) and start_date is None

    if try_realtime:
        # Try to get realtime prices for all symbols
        realtime_tasks = [_get_realtime_price(symbol) for symbol in symbols]
        realtime_results = await asyncio.gather(*realtime_tasks, return_exceptions=True)

        for symbol, rt_result in zip(symbols, realtime_results):
            if isinstance(rt_result, dict) and rt_result.get("status") == "success":
                results[symbol] = {
                    "status": "success",
                    "data": {
                        "symbol": symbol,
                        "latest": rt_result,
                        "data": [rt_result],  # Single data point for consistency
                        "is_realtime": True
                    }
                }
            # If realtime fails, we'll fall back to daily data below

    # Get symbols that don't have realtime data yet
    symbols_need_daily = [s for s in symbols if s not in results]

    if symbols_need_daily:
        table_name = 'stock.stock_prices_1d'

        now = datetime.datetime.now()
        end_filter = datetime.datetime.strptime(end_date, '%Y-%m-%d') if end_date else now

        if start_date:
            start_filter = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        elif lookback_days is not None:
            start_filter = end_filter - datetime.timedelta(days=lookback_days)
        else:
            start_filter = end_filter - datetime.timedelta(days=30)

        start_date_str = start_filter.strftime('%Y-%m-%d')
        end_date_str = end_filter.strftime('%Y-%m-%d')

        # Fetch daily data concurrently
        tasks = [
            _get_single_stock_data(symbol, table_name, start_date_str, end_date_str)
            for symbol in symbols_need_daily
        ]

        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for symbol, data_result in zip(symbols_need_daily, task_results):
            if isinstance(data_result, Exception):
                error_msg = str(data_result)
                results[symbol] = {"status": "error", "message": error_msg}
                errors.append(f"{symbol}: {error_msg}")
            elif data_result["status"] == "success":
                result_data = data_result["result"]
                result_data["is_realtime"] = False
                results[symbol] = {"status": "success", "data": result_data}
            else:
                results[symbol] = {"status": "error", "message": data_result["message"]}
                errors.append(f"{symbol}: {data_result['message']}")

    if errors:
        return {"status": "partial_success", "results": results, "errors": errors}
    return {"status": "success", "results": results}


async def get_stock_price_prediction_mcp(symbols: list[str], table_type: str) -> dict:
    """
    MCP version of get_stock_price_prediction

    Args:
        symbols: List of stock symbols
        table_type: Prediction type ('3d' or '48d')

    Returns:
        dict: Dictionary containing prediction results
    """
    def _sync_fetch_prediction(symbol: str, table_type: str) -> dict:
        try:
            symbol = symbol.upper()

            if table_type == "3d":
                table_name = "stock.stock_prices_3d_predict"
                prediction_columns = ["close_next_1", "close_next_2", "close_next_3"]
                max_days = 3
            elif table_type == "48d":
                table_name = "stock.stock_prices_48d_predict"
                prediction_columns = [f"close_next_{i}" for i in range(1, 49)]
                max_days = 48
            else:
                raise ValueError(f"Invalid table_type: {table_type}")

            columns_str = ", ".join([f"p.{col}" for col in prediction_columns])

            sql_query = f"""
            WITH LatestPrice AS (
                SELECT ticker, time, close
                FROM stock.stock_prices_1d
                WHERE ticker = '{symbol}'
                ORDER BY time DESC
                LIMIT 1
            )
            SELECT
                lp.ticker,
                lp.time AS prediction_made_date,
                lp.close AS current_close,
                {columns_str}
            FROM LatestPrice lp
            LEFT JOIN {table_name} p ON lp.ticker = p.ticker AND lp.time = p.time;
            """

            records, is_error = execute_sql_in_thread(sql_query)

            if is_error or not records:
                raise Exception("No prediction data found")

            result_data = records[0]
            has_prediction_data = any(result_data.get(col) is not None for col in prediction_columns)

            if not has_prediction_data:
                raise Exception(f"No prediction data for {symbol}")

            current_price = serialize_val(result_data.get('current_close'))
            prediction_date = serialize_val(result_data.get('prediction_made_date'))

            predictions_list = []
            if isinstance(current_price, (int, float)) and current_price != 0:
                for i, col in enumerate(prediction_columns):
                    pred_val = serialize_val(result_data.get(col))
                    day_pred = {'day': i + 1, 'predicted_close': pred_val, 'percent_change': None}
                    if isinstance(pred_val, (int, float)):
                        try:
                            day_pred['percent_change'] = round(((pred_val / current_price) - 1) * 100, 2)
                        except TypeError:
                            pass
                    predictions_list.append(day_pred)

            result = {
                'symbol': symbol,
                'table_type': table_type,
                'predict_date': prediction_date,
                'current_price': current_price,
                'max_days': max_days,
                'predictions': predictions_list,
            }

            return {"status": "success", "result": result}

        except Exception as e:
            logger.error(f"Error fetching prediction for {symbol}: {e}")
            return {"status": "error", "message": str(e)}

    # Run in thread pool using asyncio.to_thread
    tasks = [
        asyncio.to_thread(_sync_fetch_prediction, symbol, table_type)
        for symbol in symbols
    ]

    task_results = await asyncio.gather(*tasks, return_exceptions=True)

    results = {}
    errors = []

    for symbol, pred_result in zip(symbols, task_results):
        if isinstance(pred_result, Exception):
            error_msg = str(pred_result)
            results[symbol] = {"status": "error", "message": error_msg}
            errors.append(f"{symbol}: {error_msg}")
        elif pred_result["status"] == "success":
            results[symbol] = pred_result
        else:
            results[symbol] = pred_result
            errors.append(f"{symbol}: {pred_result['message']}")

    if errors:
        return {"status": "partial_success", "results": results, "errors": errors}
    return {"status": "success", "results": results}


def _create_candlestick_chart(symbol: str, stock_data: dict, interval: str = "1D") -> dict:
    """
    Create a candlestick chart with volume from stock data.

    Args:
        symbol: Stock symbol
        stock_data: Stock data dictionary with 'data' key
        interval: Time interval for chart

    Returns:
        Dictionary with status and path or error message
    """
    try:
        if not stock_data or 'data' not in stock_data or not stock_data['data']:
            return {"status": "error", "message": f"No price data for {symbol}"}

        # Convert data to DataFrame
        df_data = []
        for record in stock_data['data']:
            df_data.append({
                'Date': pd.to_datetime(record['time']),
                'Open': float(record['open']),
                'High': float(record['high']),
                'Low': float(record['low']),
                'Close': float(record['close']),
                'Volume': int(record['volume']) if record.get('volume') else 0
            })

        df = pd.DataFrame(df_data)
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)

        if df.empty:
            return {"status": "error", "message": f"Empty data for {symbol}"}

        # Create temporary file for chart
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        # Configure chart style
        mc = mpf.make_marketcolors(
            up='g', down='r',
            edge='inherit',
            wick={'up':'green', 'down':'red'},
            volume='in'
        )

        s = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle='-',
            y_on_right=True
        )

        # Create the chart
        mpf.plot(
            df,
            type='candle',
            style=s,
            volume=True,
            title=f'{symbol} - Candlestick Chart with Volume',
            ylabel='Price (VND)',
            ylabel_lower='Volume',
            figsize=(12, 8),
            savefig=dict(fname=tmp_path, dpi=300, bbox_inches='tight')
        )

        logger.info(f"Chart created successfully for {symbol} at {tmp_path}")
        return {"status": "success", "path": tmp_path, "symbol": symbol}

    except Exception as e:
        logger.error(f"Error creating chart for {symbol}: {str(e)}")
        return {"status": "error", "message": str(e), "symbol": symbol}


async def generate_chart_from_data_mcp(
    symbols: list[str],
    interval: str = "1D",
    lookback_days: int = 30,
    chart_type: str = "candlestick"
) -> dict:
    """
    MCP version of generate_chart_from_data
    Fetches stock data and generates candlestick charts

    OPTIMIZED: Sử dụng FastChartGenerator với template caching
    - Lần đầu: ~1.5s (tạo template)
    - Các lần sau: ~0.3-0.5s (chỉ update data)

    Args:
        symbols: List of stock symbols
        interval: Time interval (default: '1D')
        lookback_days: Number of days to look back for data
        chart_type: "candlestick" hoặc "line" (default: "candlestick")

    Returns:
        dict: Dictionary with chart generation results
    """
    try:
        # First, fetch stock data for all symbols
        stock_data_result = await get_stock_data_mcp(
            symbols=symbols,
            interval=interval,
            lookback_days=lookback_days,
            realtime=False  # Không cần realtime cho chart
        )

        if stock_data_result['status'] == 'error':
            return stock_data_result

        # Generate charts for each symbol using FastChartGenerator
        chart_results = {}
        errors = []

        for symbol in symbols:
            symbol_data = stock_data_result['results'].get(symbol, {})

            if symbol_data.get('status') == 'error':
                chart_results[symbol] = {
                    "status": "error",
                    "message": symbol_data.get('message'),
                    "symbol": symbol
                }
                errors.append(f"{symbol}: {symbol_data.get('message')}")
                continue

            # Lấy data để vẽ chart
            data = symbol_data.get('data', {}).get('data', [])

            if not data:
                chart_results[symbol] = {
                    "status": "error",
                    "message": "No price data available",
                    "symbol": symbol
                }
                errors.append(f"{symbol}: No price data available")
                continue

            # Sử dụng FastChartGenerator (template caching)
            result = await generate_fast_chart(
                symbol=symbol,
                data=data,
                chart_type=chart_type,
                title=f"{symbol} - {'Candlestick' if chart_type == 'candlestick' else 'Price'} Chart"
            )

            if result['status'] == 'success':
                chart_results[symbol] = {
                    "status": "success",
                    "chart_path": result['chart_path'],
                    "data_points": result.get('data_points', 0),
                    "message": f"Chart generated successfully for {symbol}"
                }
            else:
                chart_results[symbol] = result
                errors.append(f"{symbol}: {result.get('message')}")

        if errors:
            return {
                "status": "partial_success",
                "results": chart_results,
                "errors": errors,
                "message": f"Generated {len(chart_results) - len(errors)}/{len(symbols)} charts successfully"
            }

        return {
            "status": "success",
            "results": chart_results,
            "message": f"Successfully generated charts for all {len(symbols)} symbols"
        }

    except Exception as e:
        logger.error(f"Error in generate_chart_from_data_mcp: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "symbols": symbols
        }


async def get_stock_details_from_tcbs_mcp(symbols: list[str]) -> dict:
    """
    MCP version of stock_search_filter_tool
    Get detailed stock information from TCBS/VCI for specific symbols
    Uses VCI as fallback when TCBS is unavailable

    Args:
        symbols: List of stock symbols to get details for

    Returns:
        dict: Dictionary containing detailed stock data
    """
    def _sync_get_tcbs_details(symbols: list[str]) -> dict:
        """Synchronous function to get TCBS details"""
        try:
            import pandas as pd
            import numpy as np
            from vnstock import Vnstock

            # Try TCBS first
            try:
                stock = Vnstock().stock(symbol='ACB', source='TCBS')
                params = {"exchangeName": "HOSE,HNX,UPCOM"}
                all_stocks_df = stock.screener.stock(params=params, limit=1700)
            except Exception as tcbs_error:
                logger.warning(f"TCBS unavailable: {tcbs_error}, falling back to VCI")
                all_stocks_df = pd.DataFrame()

            # Fallback to VCI if TCBS fails
            if all_stocks_df.empty:
                logger.info("Using VCI fallback for stock details")
                result_data = []

                for symbol in symbols:
                    try:
                        vci_stock = Vnstock().stock(symbol=symbol.upper(), source='VCI')

                        # Get overview
                        overview = vci_stock.company.overview()
                        overview_data = overview.to_dict(orient='records')[0] if not overview.empty else {}

                        # Get financial ratios
                        ratios = vci_stock.finance.ratio(period='quarter')
                        latest_ratios = ratios.to_dict(orient='records')[0] if not ratios.empty else {}

                        # Get price history
                        history = vci_stock.quote.history(start='2026-01-01', end='2026-01-12')
                        latest_price = history.to_dict(orient='records')[-1] if not history.empty else {}

                        # Combine data
                        stock_data = {
                            'ticker': symbol.upper(),
                            'close': latest_price.get('close'),
                            'volume': latest_price.get('volume'),
                            **{k: v for k, v in overview_data.items() if k != 'symbol'},
                            **{k: v for k, v in latest_ratios.items() if k not in ['ticker', 'symbol']},
                            'source': 'VCI'
                        }

                        # Clean NaN values
                        stock_data = {k: (None if pd.isna(v) else v) for k, v in stock_data.items()}
                        result_data.append(stock_data)

                    except Exception as e:
                        logger.warning(f"Error fetching VCI data for {symbol}: {e}")
                        result_data.append({
                            'ticker': symbol.upper(),
                            'error': str(e),
                            'source': 'VCI'
                        })

                return {
                    "status": "success" if result_data else "error",
                    "message": f"Found {len(result_data)} stock(s) from VCI",
                    "count": len(result_data),
                    "data": result_data,
                    "source": "VCI"
                }

            # TCBS worked - process as before
            filtered_df = all_stocks_df[all_stocks_df['ticker'].isin(symbols)]

            if filtered_df.empty:
                return {
                    "status": "warning",
                    "message": f"No data found for symbols: {', '.join(symbols)}",
                    "data": []
                }

            # Define the fields to keep
            fields_to_keep = [
                'ticker', 'exchange', 'industry', 'market_cap',
                'roe', 'alpha', 'beta', 'pe', 'pb', 'eps', 'ev_ebitda',
                'dividend_yield', 'gross_margin', 'net_margin', 'doe',
                'profit_last_4q', 'net_cash_per_market_cap', 'net_cash_per_total_assets',
                'revenue_growth_1y', 'revenue_growth_5y', 'eps_growth_1y', 'eps_growth_5y',
                'last_quarter_revenue_growth', 'second_quarter_revenue_growth',
                'last_quarter_profit_growth', 'second_quarter_profit_growth',
                'rsi14', 'rsi14_status', 'price_growth_1w', 'price_growth_1m',
                'prev_1d_growth_pct', 'prev_1m_growth_pct', 'prev_1y_growth_pct', 'prev_5y_growth_pct',
                'pct_1y_from_peak', 'pct_away_from_hist_peak', 'pct_1y_from_bottom', 'pct_off_hist_bottom',
                'avg_trading_value_5d', 'avg_trading_value_10d', 'avg_trading_value_20d',
                'total_trading_value', 'foreign_vol_pct', 'foreign_buysell_20s',
                'free_transfer_rate', 'foreign_transaction', 'num_increase_continuous_day', 'num_decrease_continuous_day',
                'price_vs_sma5', 'price_vs_sma10', 'price_vs_sma20', 'price_vs_sma50', 'price_vs_sma100',
                'vol_vs_sma5', 'vol_vs_sma10', 'vol_vs_sma20', 'vol_vs_sma50',
                'macd_histogram', 'bolling_band_signal', 'price_break_out52_week', 'price_wash_out52_week',
                'close', 'change_percent_1d', 'volume'
            ]

            available_fields = [field for field in fields_to_keep if field in filtered_df.columns]
            filtered_df = filtered_df[available_fields]
            filtered_df = filtered_df.replace({np.nan: None})
            result_data = filtered_df.to_dict(orient='records')

            return {
                "status": "success",
                "message": f"Found {len(result_data)} stock(s)",
                "count": len(result_data),
                "data": result_data,
                "source": "TCBS"
            }

        except Exception as e:
            logger.error(f"Error in _sync_get_tcbs_details: {str(e)}")
            return {
                "status": "error",
                "message": f"Error fetching data: {str(e)}",
                "data": []
            }

    try:
        result = await asyncio.to_thread(_sync_get_tcbs_details, symbols)
        return result

    except Exception as e:
        logger.error(f"Error in get_stock_details_from_tcbs_mcp: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "symbols": symbols,
            "data": []
        }
