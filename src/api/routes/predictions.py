"""
API routes cho predictions
"""

from fastapi import APIRouter, HTTPException
import logging

from src.api.services.stock_services import StockService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["predictions"])
stock_service = StockService()


@router.get("/{ticker}")
async def get_predictions(ticker: str):
    """Lấy predictions cho ticker"""
    ticker = ticker.upper()
    predictions = stock_service.get_predictions(ticker)

    if not predictions:
        raise HTTPException(
            status_code=404, detail=f"No predictions found for {ticker}"
        )

    return {"ticker": ticker, "predictions": predictions}


@router.get("/{ticker}/3day")
async def get_3day_prediction(ticker: str):
    """Lấy dự đoán 3 ngày"""
    ticker = ticker.upper()
    predictions = stock_service.get_predictions(ticker)

    if not predictions or "3day" not in predictions:
        raise HTTPException(
            status_code=404, detail=f"No 3-day predictions for {ticker}"
        )

    return {
        "ticker": ticker,
        "type": "3day",
        "prediction_time": predictions["3day"]["time"],
        "predictions": predictions["3day"]["predictions"],
    }
    

