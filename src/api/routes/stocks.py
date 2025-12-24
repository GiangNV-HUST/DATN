"""
API routes cho stocks
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from src.api.services.stock_services import StockService
from src.api.models.schemas import (
    StockListResponse,
    StockPriceWithIndicators,
    StockSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["stocks"])
stock_service = StockService()


@router.get("/", response_model=StockListResponse)
async def get_all_stocks():
    """Lấy giá tất cả các cổ phiếu"""
    tickers = stock_service.get_all_tickers()
    return {"tickers": tickers, "total": len(tickers)}


@router.get("/{ticker}/summary", response_model=StockSummary)
async def get_stock_summary(ticker: str):
    """Lấy tóm tắt cổ phiếu"""
    ticker = ticker.upper()
    summary = stock_service.get_stock_summary(ticker)

    if not summary:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

    return summary


@router.get("/{ticker}/history")
async def get_stock_history(
    ticker: str,
    days: int = Query(default=30, ge=1, le=365, description="Số ngày lịch sử"),
):
    """Lấy lịch sử giá cổ phiếu"""
    ticker = ticker.upper()
    history = stock_service.get_stock_history(ticker, days)

    if not history:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")
    return {"ticker": ticker, "days": days, "data": history}


@router.get("/{ticker}/latest")
async def get_latest_price(ticker: str):
    """Lấy giá mới nhất"""
    ticker = ticker.upper()
    latest = stock_service.get_latest_price(ticker)

    if not latest:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

    return latest


@router.get("/search/")
async def search_stocks(
    rsi_min: Optional[float] = Query(None, ge=0, le=100),
    rsi_max: Optional[float] = Query(None, ge=0, le=100),
    volume_min: Optional[float] = Query(None, ge=0),
):
    """Tìm kiếm cổ phiếu theo tiêu chí"""
    tickers = stock_service.search_stocks(rsi_min, rsi_max, volume_min)
    return {
        "tickers": tickers,
        "total": len(tickers),
        "criteria": {"rsi_min": rsi_min, "rsi_max": rsi_max, "volume_min": volume_min},
    }
