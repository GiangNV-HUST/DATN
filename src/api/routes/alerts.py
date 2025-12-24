"""
API routes cho alerts
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging

from src.api.services.stock_services import StockService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])
stock_service = StockService()


@router.get("/")
async def get_alerts(
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    limit: int = Query(50, ge=1, le=200, description="Number of alerts"),
    alert_type: Optional[str] = Query(None, description="Type: 'user' or 'technical' (default: technical)"),
):
    """
    Lấy danh sách alerts
    - alert_type='user': Lấy user alerts (do người dùng tạo)
    - alert_type='technical': Lấy technical alerts (do hệ thống phát hiện)
    - Mặc định: technical alerts
    """
    if alert_type == "user":
        alerts = stock_service.get_recent_alerts(ticker=ticker, limit=limit)
    else:
        # Mặc định lấy technical alerts
        alerts = stock_service.get_technical_alerts(ticker=ticker, limit=limit)

    return {"alerts": alerts, "total": len(alerts), "ticker": ticker, "type": alert_type or "technical"}


@router.get("/technical")
async def get_technical_alerts(
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    limit: int = Query(50, ge=1, le=200, description="Number of alerts"),
    alert_level: Optional[str] = Query(None, description="Filter by level: critical, warning, info"),
):
    """Lấy technical alerts (cảnh báo kỹ thuật tự động)"""
    alerts = stock_service.get_technical_alerts(ticker=ticker, limit=limit, alert_level=alert_level)

    return {"alerts": alerts, "total": len(alerts), "ticker": ticker, "alert_level": alert_level}


@router.get("/user")
async def get_user_alerts(
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    limit: int = Query(50, ge=1, le=200, description="Number of alerts"),
):
    """Lấy user alerts (do người dùng tạo)"""
    alerts = stock_service.get_recent_alerts(ticker=ticker, limit=limit)

    return {"alerts": alerts, "total": len(alerts), "ticker": ticker}


@router.get("/{ticker}")
async def get_alerts_by_ticker(
    ticker: str,
    limit: int = Query(50, ge=1, le=200),
    alert_type: Optional[str] = Query(None, description="Type: 'user' or 'technical' (default: technical)"),
):
    """Lấy alerts của một ticker"""
    ticker = ticker.upper()

    if alert_type == "user":
        alerts = stock_service.get_recent_alerts(ticker=ticker, limit=limit)
    else:
        # Mặc định lấy technical alerts
        alerts = stock_service.get_technical_alerts(ticker=ticker, limit=limit)

    return {"ticker": ticker, "alerts": alerts, "total": len(alerts), "type": alert_type or "technical"}

