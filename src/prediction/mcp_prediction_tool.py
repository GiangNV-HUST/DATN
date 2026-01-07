"""
MCP Tool for Stock Price Prediction using Ensemble Model

This module provides MCP-compatible async functions for stock price forecasting.
Can be integrated into the MCP Server to be called by AI agents.
"""

import asyncio
import pandas as pd
from typing import Dict, Optional, List
from datetime import datetime, timedelta

# Import prediction service
from src.prediction.prediction_service import get_prediction_service


async def get_stock_price_prediction(
    ticker: str,
    horizon: str = "3day",
    data_source: str = "database"
) -> Dict:
    """
    Get stock price prediction using ensemble model

    This is an async MCP tool that can be called by AI agents.

    Args:
        ticker: Stock ticker symbol (e.g., 'VCB', 'VHM')
        horizon: Forecast horizon - '3day' or '48day'
        data_source: Where to fetch data from ('database' or 'api')

    Returns:
        Dictionary with prediction results:
        {
            "status": "success" | "error",
            "ticker": str,
            "horizon": str,
            "current_price": float,
            "predicted_price": float,
            "change_percent": float,
            "confidence_lower": float,
            "confidence_upper": float,
            "prediction_date": str (ISO format),
            "target_date": str (ISO format),
            "message": str (optional, for errors)
        }

    Example:
        result = await get_stock_price_prediction("VCB", "3day")
        print(f"VCB predicted: {result['predicted_price']}")
    """
    try:
        # Validate horizon
        if horizon not in ["3day", "48day"]:
            return {
                "status": "error",
                "ticker": ticker,
                "horizon": horizon,
                "message": f"Invalid horizon: {horizon}. Must be '3day' or '48day'"
            }

        # Get prediction service
        service = get_prediction_service()

        # Fetch historical data
        # Run in executor to avoid blocking (since pandas/DB ops are sync)
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            fetch_stock_data,
            ticker,
            data_source
        )

        if data is None or len(data) < 100:
            return {
                "status": "error",
                "ticker": ticker,
                "horizon": horizon,
                "message": f"Insufficient data for {ticker}. Need at least 100 days of history."
            }

        # Make prediction (run in executor)
        result = await loop.run_in_executor(
            None,
            service.predict,
            ticker,
            data,
            horizon
        )

        result["status"] = "success"
        return result

    except FileNotFoundError as e:
        return {
            "status": "error",
            "ticker": ticker,
            "horizon": horizon,
            "message": f"Model not trained for {ticker} ({horizon}). Please train first."
        }

    except Exception as e:
        return {
            "status": "error",
            "ticker": ticker,
            "horizon": horizon,
            "message": f"Prediction error: {str(e)}"
        }


async def get_stock_prediction_batch(
    tickers: List[str],
    horizon: str = "3day"
) -> List[Dict]:
    """
    Get predictions for multiple stocks in batch

    Args:
        tickers: List of stock ticker symbols
        horizon: Forecast horizon

    Returns:
        List of prediction results (one per ticker)

    Example:
        results = await get_stock_prediction_batch(["VCB", "VHM", "VIC"], "3day")
    """
    # Run predictions in parallel
    tasks = [
        get_stock_price_prediction(ticker, horizon)
        for ticker in tickers
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert exceptions to error dicts
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                "status": "error",
                "ticker": tickers[i],
                "horizon": horizon,
                "message": str(result)
            })
        else:
            processed_results.append(result)

    return processed_results


async def get_available_prediction_models() -> Dict:
    """
    Get list of available trained models

    Returns:
        Dictionary with:
        {
            "status": "success",
            "models": [
                {
                    "ticker": str,
                    "horizon": str,
                    "file_size_mb": float,
                    "modified_date": str
                },
                ...
            ],
            "count": int
        }

    Example:
        result = await get_available_prediction_models()
        print(f"Found {result['count']} trained models")
    """
    try:
        service = get_prediction_service()

        loop = asyncio.get_event_loop()
        models = await loop.run_in_executor(
            None,
            service.get_available_models
        )

        return {
            "status": "success",
            "models": models,
            "count": len(models)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "count": 0,
            "models": []
        }


def fetch_stock_data(ticker: str, data_source: str = "database") -> Optional[pd.DataFrame]:
    """
    Fetch stock data from database or API

    Args:
        ticker: Stock ticker symbol
        data_source: 'database' or 'api'

    Returns:
        DataFrame with OHLCV data or None if error

    Note:
        This is a synchronous helper function.
        Replace with actual database/API implementation.
    """
    try:
        if data_source == "database":
            # TODO: Replace with actual database query
            # from src.database.connection import get_connection
            # conn = get_connection()
            # query = f"""
            #     SELECT time, open, high, low, close, volume
            #     FROM stock_prices
            #     WHERE ticker = '{ticker}'
            #     ORDER BY time DESC
            #     LIMIT 200
            # """
            # df = pd.read_sql(query, conn)
            # df = df.sort_values('time')
            # df = df.set_index('time')
            # return df

            # Temporary: Return None to indicate not implemented
            return None

        elif data_source == "api":
            # TODO: Fetch from API (vnstock, etc.)
            # from vnstock import stock_historical_data
            # df = stock_historical_data(ticker, start='2023-01-01', end='2024-12-31')
            # return df

            return None

        else:
            raise ValueError(f"Invalid data_source: {data_source}")

    except Exception as e:
        print(f"❌ Error fetching data for {ticker}: {e}")
        return None


# MCP Tool Metadata (for MCP Server registration)
MCP_TOOLS = {
    "get_stock_price_prediction": {
        "name": "get_stock_price_prediction",
        "description": "Get stock price prediction using ensemble 5-model (PatchTST, LightGBM, LSTM, Prophet, XGBoost). Returns predicted price, confidence interval, and expected change.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., VCB, VHM, VIC)"
                },
                "horizon": {
                    "type": "string",
                    "enum": ["3day", "48day"],
                    "description": "Forecast horizon: '3day' for 3-day ahead, '48day' for 48-day ahead",
                    "default": "3day"
                },
                "data_source": {
                    "type": "string",
                    "enum": ["database", "api"],
                    "description": "Data source for historical prices",
                    "default": "database"
                }
            },
            "required": ["ticker"]
        }
    },

    "get_stock_prediction_batch": {
        "name": "get_stock_prediction_batch",
        "description": "Get predictions for multiple stocks in parallel. More efficient than calling get_stock_price_prediction multiple times.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of stock ticker symbols"
                },
                "horizon": {
                    "type": "string",
                    "enum": ["3day", "48day"],
                    "description": "Forecast horizon",
                    "default": "3day"
                }
            },
            "required": ["tickers"]
        }
    },

    "get_available_prediction_models": {
        "name": "get_available_prediction_models",
        "description": "List all trained prediction models available for use. Returns ticker, horizon, and model metadata.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}


# For testing
if __name__ == "__main__":
    async def test():
        print("🧪 Testing MCP Prediction Tools")
        print("=" * 50)

        # Test 1: Get available models
        print("\n1️⃣ Get available models:")
        result = await get_available_prediction_models()
        print(f"Status: {result['status']}")
        print(f"Count: {result['count']}")
        if result['models']:
            for model in result['models'][:3]:
                print(f"  - {model['ticker']} ({model['horizon']})")

        # Test 2: Single prediction (will fail without data)
        print("\n2️⃣ Single prediction (VCB, 3day):")
        result = await get_stock_price_prediction("VCB", "3day")
        print(f"Status: {result['status']}")
        if result['status'] == 'error':
            print(f"Message: {result['message']}")
        else:
            print(f"Predicted: {result['predicted_price']:.2f}")
            print(f"Change: {result['change_percent']:.2f}%")

        # Test 3: Batch prediction
        print("\n3️⃣ Batch prediction (VCB, VHM, VIC):")
        results = await get_stock_prediction_batch(["VCB", "VHM", "VIC"], "3day")
        for res in results:
            print(f"  {res['ticker']}: {res['status']}")

    asyncio.run(test())
