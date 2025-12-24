"""
Pydantic schemas cho API validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class StockPrice(BaseModel):
    """Schema cho giá cổ phiếu"""

    ticker: str
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None


class StockPriceWithIndicators(StockPrice):
    """Schema cho giá cổ phiếu kèm indicators"""

    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma50: Optional[float] = None
    ma100: Optional[float] = None
    rsi: Optional[float] = None
    macd_main: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_diff: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None


class PredictionResponse(BaseModel):
    """Schema cho predictions"""

    ticker: str
    prediction_time: datetime
    predictions: List[float]
    prediction_type: str  # "3day" hoặc "48day"


class AlertResponse(BaseModel):
    """Schema cho alerts"""

    id: Optional[int] = None
    ticker: str
    alert_type: str
    alert_level: str  # "info", "warning", "critical"
    message: str
    create_at: datetime


class StockListResponse(BaseModel):
    """Schema cho danh sách cổ phiếu"""

    tickers: List[str]
    total: int


class StockSummary(BaseModel):
    """Schema cho tóm tắt cổ phiếu"""

    ticker: str
    latest_price: float
    change_percent: Optional[float] = None
    rsi: Optional[float] = None
    volume: Optional[float] = None
    last_updated: datetime


# BaseModel: Kế thừa từ Pydantic để validate dữ liệu
# Optional: Field có thể None
# List: Danh sách các items
