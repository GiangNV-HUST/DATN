"""
Margin Call Handler - Xử lý cascading margin calls

Margin call cascade là kịch bản đặc biệt nguy hiểm trong thị trường Việt Nam.
Khi thị trường giảm mạnh, các nhà đầu tư margin (vay tiền) bị ép bán để đảm bảo
tỷ lệ ký quỹ (margin ratio). Việc bán ép này khiến giá giảm thêm, gây ra thêm
margin calls → Vòng xoáy chết (death spiral).

Đặc điểm:
- Xảy ra khi VN-Index giảm >5% trong vài ngày
- Các cổ phiếu margin (high margin debt) bị ảnh hưởng nặng nhất
- Tự củng cố (self-reinforcing): Bán → Giảm giá → Thêm margin call → Bán thêm
- Duration: Thường kéo dài 5-7 ngày cho đến khi margin debt giảm xuống
- Overshooting: Giá giảm quá mức fundamentals (panic selling)

Phases:
1. Trigger: Thị trường giảm 5-7%, margin calls bắt đầu
2. Cascade: Bán ép liên tục, giá giảm 10-15% thêm
3. Panic: Volume spike, indiscriminate selling
4. Exhaustion: Margin debt đã giảm, selling pressure giảm
5. Recovery: Bargain hunters vào, giá bounce back
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from enum import Enum


class MarginCrisisLevel(Enum):
    """Mức độ nghiêm trọng của margin call cascade"""
    NORMAL = "normal"              # Không có nguy cơ
    WARNING = "warning"            # Cảnh báo sớm (thị trường giảm 3-5%)
    TRIGGER = "trigger"            # Margin calls bắt đầu (5-7%)
    CASCADE = "cascade"            # Cascade đang xảy ra (7-12%)
    PANIC = "panic"                # Panic selling (>12%)
    EXHAUSTION = "exhaustion"      # Selling exhausted
    RECOVERY = "recovery"          # Phục hồi


class MarginCallHandler:
    """
    Handler cho margin call cascade scenarios.

    Xử lý:
    1. Detect margin call risk từ market conditions
    2. Identify stocks với high margin debt (high risk)
    3. Adjust predictions trong cascade period
    4. Detect exhaustion và recovery signals
    5. Generate defensive recommendations
    """

    def __init__(self):
        """Initialize Margin Call Handler"""
        # Margin debt thresholds (as % of total market cap)
        self.margin_debt_thresholds = {
            'low': 0.05,      # <5% market cap
            'medium': 0.10,   # 5-10%
            'high': 0.15,     # 10-15%
            'extreme': 0.20   # >15%
        }

        # VN-Index drop thresholds for margin call risk
        self.vnindex_thresholds = {
            'warning': -0.03,    # -3%
            'trigger': -0.05,    # -5%
            'cascade': -0.07,    # -7%
            'panic': -0.12       # -12%
        }

        # Stocks with historically high margin debt (need to update from data)
        self.high_margin_stocks = [
            'HPG', 'VHM', 'VIC', 'MSN', 'STB', 'TCB', 'VPB', 'HDB',
            'FPT', 'MWG', 'SSI', 'VND', 'VRE', 'NVL', 'PDR', 'DGW'
        ]

        # Historical cascade stats
        self.historical_cascades = {
            'average_duration': 6,  # days
            'average_drawdown': -0.18,  # -18%
            'average_recovery': 0.10,  # +10% bounce from bottom
            'recovery_duration': 10  # days
        }

        # Current cascade tracking
        self.active_cascade = None

    def detect_market_stress(self, vnindex_prices: pd.Series,
                            window: int = 14) -> Tuple[MarginCrisisLevel, Dict]:
        """
        Detect market stress level từ VN-Index movement.

        Args:
            vnindex_prices: Series của VN-Index prices (recent first)
            window: Lookback window (days)

        Returns:
            (crisis_level, details)
        """
        if len(vnindex_prices) < window:
            return MarginCrisisLevel.NORMAL, {'error': 'Insufficient data'}

        # Calculate metrics
        current_price = vnindex_prices.iloc[0]
        prices_window = vnindex_prices.iloc[:window]

        # Recent performance
        change_1d = (current_price / vnindex_prices.iloc[1] - 1) if len(vnindex_prices) > 1 else 0
        change_3d = (current_price / vnindex_prices.iloc[3] - 1) if len(vnindex_prices) > 3 else 0
        change_7d = (current_price / vnindex_prices.iloc[7] - 1) if len(vnindex_prices) > 7 else 0
        change_14d = (current_price / vnindex_prices.iloc[14] - 1) if len(vnindex_prices) > 14 else 0

        # Volatility
        returns = vnindex_prices.pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # Annualized

        # Drawdown from recent peak
        peak = prices_window.max()
        drawdown = (current_price / peak - 1)

        # Volume analysis (placeholder - need actual volume data)
        volume_spike = False  # TODO: Check if volume > 1.5x average

        # Determine crisis level
        if drawdown <= self.vnindex_thresholds['panic']:
            level = MarginCrisisLevel.PANIC
        elif drawdown <= self.vnindex_thresholds['cascade']:
            level = MarginCrisisLevel.CASCADE
        elif drawdown <= self.vnindex_thresholds['trigger']:
            level = MarginCrisisLevel.TRIGGER
        elif drawdown <= self.vnindex_thresholds['warning']:
            level = MarginCrisisLevel.WARNING
        else:
            level = MarginCrisisLevel.NORMAL

        details = {
            'current_price': current_price,
            'change_1d': change_1d,
            'change_3d': change_3d,
            'change_7d': change_7d,
            'change_14d': change_14d,
            'drawdown': drawdown,
            'peak_price': peak,
            'volatility': volatility,
            'volume_spike': volume_spike
        }

        return level, details

    def check_margin_debt_level(self, ticker: str, margin_debt_vnd: float,
                                market_cap_vnd: float) -> Tuple[str, float, Dict]:
        """
        Kiểm tra mức độ margin debt của cổ phiếu.

        Args:
            ticker: Mã cổ phiếu
            margin_debt_vnd: Margin debt hiện tại (VND)
            market_cap_vnd: Market cap (VND)

        Returns:
            (risk_level, margin_ratio, details)
        """
        # Calculate margin debt ratio
        margin_ratio = margin_debt_vnd / market_cap_vnd

        # Determine risk level
        if margin_ratio >= self.margin_debt_thresholds['extreme']:
            risk_level = "EXTREME"
        elif margin_ratio >= self.margin_debt_thresholds['high']:
            risk_level = "HIGH"
        elif margin_ratio >= self.margin_debt_thresholds['medium']:
            risk_level = "MEDIUM"
        elif margin_ratio >= self.margin_debt_thresholds['low']:
            risk_level = "LOW"
        else:
            risk_level = "MINIMAL"

        # Additional checks
        is_high_margin_stock = ticker in self.high_margin_stocks

        details = {
            'margin_debt_vnd': margin_debt_vnd,
            'market_cap_vnd': market_cap_vnd,
            'margin_ratio': margin_ratio,
            'risk_level': risk_level,
            'is_high_margin_stock': is_high_margin_stock,
            'threshold_extreme': self.margin_debt_thresholds['extreme'],
            'distance_to_extreme': self.margin_debt_thresholds['extreme'] - margin_ratio
        }

        return risk_level, margin_ratio, details

    def detect_cascade_phase(self, crisis_level: MarginCrisisLevel,
                            days_since_trigger: int,
                            price_change_since_trigger: float,
                            volume_trend: str = "unknown") -> str:
        """
        Xác định phase hiện tại của cascade.

        Args:
            crisis_level: Mức độ khủng hoảng
            days_since_trigger: Số ngày kể từ khi trigger
            price_change_since_trigger: % thay đổi giá từ trigger point
            volume_trend: "rising", "falling", "unknown"

        Returns:
            Phase: "trigger", "cascade", "panic", "exhaustion", "recovery"
        """
        if crisis_level == MarginCrisisLevel.PANIC:
            if volume_trend == "rising" and days_since_trigger <= 3:
                return "panic"
            else:
                return "exhaustion"  # Panic but volume dropping

        elif crisis_level == MarginCrisisLevel.CASCADE:
            if days_since_trigger <= 2:
                return "cascade_early"
            elif days_since_trigger <= 5:
                return "cascade_middle"
            else:
                return "cascade_late"  # Should be exhausting

        elif crisis_level == MarginCrisisLevel.TRIGGER:
            return "trigger"

        elif crisis_level in [MarginCrisisLevel.WARNING, MarginCrisisLevel.NORMAL]:
            if price_change_since_trigger > 0:
                return "recovery"
            else:
                return "normal"

        else:
            return "unknown"

    def calculate_forced_selling_pressure(self, ticker: str,
                                         margin_debt_vnd: float,
                                         current_price: float,
                                         price_drop: float,
                                         margin_ratio_requirement: float = 0.50) -> Dict:
        """
        Ước tính áp lực bán ép từ margin calls.

        Args:
            ticker: Mã cổ phiếu
            margin_debt_vnd: Margin debt
            current_price: Giá hiện tại
            price_drop: % giảm giá (âm)
            margin_ratio_requirement: Tỷ lệ ký quỹ yêu cầu (default 50%)

        Returns:
            {
                'shares_to_sell': float,
                'selling_pressure_vnd': float,
                'days_to_liquidate': float,
                'price_impact': float
            }
        """
        # Simplified model: Estimate how many shares need to be sold

        # Calculate initial equity and debt
        # Assuming investors bought on margin at higher price
        purchase_price = current_price / (1 + price_drop)  # Back-calculate
        initial_equity_ratio = 1 - margin_ratio_requirement  # e.g., 50% equity, 50% debt

        # After price drop, equity ratio changed
        current_value = current_price
        debt = margin_debt_vnd
        current_equity = current_value - debt

        # If current equity ratio < requirement, need to sell
        current_equity_ratio = current_equity / current_value if current_value > 0 else 0

        if current_equity_ratio < margin_ratio_requirement:
            # Need to restore ratio by selling
            # Simplified: sell enough to bring ratio back to requirement
            target_equity = margin_ratio_requirement * current_value
            equity_shortfall = target_equity - current_equity

            # Shares to sell
            shares_to_sell = equity_shortfall / current_price
            selling_pressure_vnd = shares_to_sell * current_price

            # Estimate liquidation timeline (assume 20% of avg daily volume can be sold per day)
            # TODO: Use actual volume data
            avg_daily_volume_vnd = 50_000_000_000  # 50B VND placeholder
            days_to_liquidate = selling_pressure_vnd / (avg_daily_volume_vnd * 0.2)

            # Price impact (simplified)
            price_impact = -0.01 * (selling_pressure_vnd / avg_daily_volume_vnd)  # 1% per day of volume

        else:
            # No margin call
            shares_to_sell = 0
            selling_pressure_vnd = 0
            days_to_liquidate = 0
            price_impact = 0

        return {
            'shares_to_sell': shares_to_sell,
            'selling_pressure_vnd': selling_pressure_vnd,
            'days_to_liquidate': days_to_liquidate,
            'price_impact': price_impact,
            'current_equity_ratio': current_equity_ratio,
            'margin_requirement': margin_ratio_requirement,
            'in_margin_call': current_equity_ratio < margin_ratio_requirement
        }

    def adjust_prediction_for_cascade(self, ticker: str, base_prediction: float,
                                     current_price: float, crisis_level: MarginCrisisLevel,
                                     cascade_phase: str, margin_risk: str,
                                     days_since_trigger: int) -> Dict:
        """
        Adjust prediction cho margin call cascade scenario.

        Args:
            ticker: Mã cổ phiếu
            base_prediction: Prediction từ ensemble model
            current_price: Giá hiện tại
            crisis_level: Mức độ khủng hoảng
            cascade_phase: Phase của cascade
            margin_risk: Margin debt risk level
            days_since_trigger: Ngày kể từ trigger

        Returns:
            {
                'adjusted_prediction': float,
                'adjustment_factor': float,
                'confidence_lower': float,
                'confidence_upper': float,
                'reasoning': str,
                'risk_level': str
            }
        """
        # Base adjustment factors
        adjustment_factor = 1.0
        confidence_multiplier = 1.0

        if crisis_level in [MarginCrisisLevel.TRIGGER, MarginCrisisLevel.CASCADE,
                           MarginCrisisLevel.PANIC]:

            # More severe for high margin debt stocks
            margin_severity = {
                'EXTREME': 1.5,
                'HIGH': 1.3,
                'MEDIUM': 1.1,
                'LOW': 1.0,
                'MINIMAL': 0.9
            }.get(margin_risk, 1.0)

            if cascade_phase == "trigger":
                # Just triggered, more downside coming
                adjustment_factor = 0.95 * (1.0 / margin_severity)  # -5% to -7.5%
                confidence_multiplier = 2.0
                reasoning = f"Margin call cascade triggered. Downside risk high for {margin_risk} margin debt."
                risk = "HIGH"

            elif cascade_phase in ["cascade_early", "cascade_middle"]:
                # Peak panic
                adjustment_factor = 0.90 * (1.0 / margin_severity)  # -10% to -15%
                confidence_multiplier = 3.0
                reasoning = f"Active margin call cascade (day {days_since_trigger}). Heavy selling pressure."
                risk = "EXTREME"

            elif cascade_phase == "cascade_late":
                # Should be exhausting
                if days_since_trigger >= 5:
                    adjustment_factor = 0.95 * (1.0 / margin_severity)
                    confidence_multiplier = 2.5
                    reasoning = f"Late cascade phase (day {days_since_trigger}). Nearing exhaustion."
                    risk = "HIGH"
                else:
                    adjustment_factor = 0.92 * (1.0 / margin_severity)
                    confidence_multiplier = 2.8
                    reasoning = "Cascade continuing. Wait for exhaustion."
                    risk = "EXTREME"

            elif cascade_phase == "panic":
                # Peak panic with volume spike
                adjustment_factor = 0.88 * (1.0 / margin_severity)  # -12% to -18%
                confidence_multiplier = 3.5
                reasoning = "PANIC selling. Avoid catching falling knife."
                risk = "EXTREME"

            elif cascade_phase == "exhaustion":
                # Selling pressure exhausted, but wait for confirmation
                adjustment_factor = 0.95 * (1.0 / margin_severity)
                confidence_multiplier = 2.0
                reasoning = "Selling exhaustion phase. Watch for reversal."
                risk = "HIGH"

            else:
                adjustment_factor = 0.97
                confidence_multiplier = 1.5
                reasoning = "Margin call risk elevated."
                risk = "MEDIUM"

        elif crisis_level == MarginCrisisLevel.WARNING:
            # Early warning
            adjustment_factor = 0.98
            confidence_multiplier = 1.2
            reasoning = "Market stress increasing. Margin call risk rising."
            risk = "MEDIUM"

        else:
            # Normal or recovery
            if cascade_phase == "recovery":
                # Post-cascade recovery
                recovery_boost = min(0.05, days_since_trigger * 0.01)  # Up to +5%
                adjustment_factor = 1.0 + recovery_boost
                confidence_multiplier = 1.5
                reasoning = f"Recovery phase (day {days_since_trigger} post-cascade). Bounce continuing."
                risk = "MEDIUM"
            else:
                adjustment_factor = 1.0
                confidence_multiplier = 1.0
                reasoning = "Normal market conditions."
                risk = "NORMAL"

        # Apply adjustment
        adjusted_prediction = base_prediction * adjustment_factor

        # Calculate confidence interval
        base_interval = abs(base_prediction - current_price) * 0.1  # 10% of prediction range
        adjusted_interval = base_interval * confidence_multiplier

        confidence_lower = adjusted_prediction - adjusted_interval
        confidence_upper = adjusted_prediction + adjusted_interval

        return {
            'adjusted_prediction': adjusted_prediction,
            'adjustment_factor': adjustment_factor,
            'confidence_lower': confidence_lower,
            'confidence_upper': confidence_upper,
            'confidence_multiplier': confidence_multiplier,
            'reasoning': reasoning,
            'risk_level': risk
        }

    def detect_exhaustion_signals(self, ticker: str, price_series: pd.Series,
                                  volume_series: Optional[pd.Series] = None) -> Dict:
        """
        Detect signals của selling exhaustion (đáy cascade).

        Signals:
        - Price declining rate slowing (giảm chậm lại)
        - Volume declining (volume giảm)
        - Intraday reversal (đảo chiều trong ngày)
        - Multiple days of similar low (testing bottom)

        Args:
            ticker: Mã cổ phiếu
            price_series: Series giá gần đây (recent first)
            volume_series: Series volume (optional)

        Returns:
            {
                'exhaustion_score': float,  # 0-1, higher = more exhausted
                'signals': List[str],
                'confidence': str,
                'likely_bottom': bool
            }
        """
        signals = []
        score = 0.0

        if len(price_series) < 5:
            return {
                'exhaustion_score': 0.0,
                'signals': ['Insufficient data'],
                'confidence': 'LOW',
                'likely_bottom': False
            }

        # Signal 1: Declining rate slowing
        change_1d = price_series.iloc[0] / price_series.iloc[1] - 1
        change_2d = price_series.iloc[1] / price_series.iloc[2] - 1
        change_3d = price_series.iloc[2] / price_series.iloc[3] - 1

        if change_1d < 0 and change_2d < 0:  # Still declining
            if abs(change_1d) < abs(change_2d):  # But slowing
                signals.append("Decline rate slowing")
                score += 0.25

        # Signal 2: Multiple days near same level (testing support)
        recent_5 = price_series.iloc[:5]
        price_range = recent_5.max() - recent_5.min()
        avg_price = recent_5.mean()
        range_pct = price_range / avg_price

        if range_pct < 0.03:  # Within 3%
            signals.append("Price consolidating near support")
            score += 0.25

        # Signal 3: Positive close (if we have intraday data - placeholder)
        # TODO: Check if close > open today
        # signals.append("Positive intraday reversal")
        # score += 0.25

        # Signal 4: Volume declining (if available)
        if volume_series is not None and len(volume_series) >= 3:
            vol_1 = volume_series.iloc[0]
            vol_2 = volume_series.iloc[1]
            vol_3 = volume_series.iloc[2]

            if vol_1 < vol_2 < vol_3:  # Declining volume
                signals.append("Volume declining (selling exhaustion)")
                score += 0.25

        # Signal 5: RSI oversold (placeholder - need calculation)
        # if rsi < 30:
        #     signals.append("RSI oversold")
        #     score += 0.1

        # Determine confidence
        if score >= 0.75:
            confidence = "HIGH"
            likely_bottom = True
        elif score >= 0.5:
            confidence = "MEDIUM"
            likely_bottom = True
        elif score >= 0.25:
            confidence = "LOW"
            likely_bottom = False
        else:
            confidence = "VERY_LOW"
            likely_bottom = False

        return {
            'exhaustion_score': score,
            'signals': signals,
            'confidence': confidence,
            'likely_bottom': likely_bottom
        }

    def generate_defensive_recommendation(self, ticker: str, crisis_level: MarginCrisisLevel,
                                         cascade_phase: str, margin_risk: str,
                                         adjustment_result: Dict) -> Dict:
        """
        Generate defensive trading recommendation during cascade.

        Args:
            ticker: Mã cổ phiếu
            crisis_level: Mức độ khủng hoảng
            cascade_phase: Phase
            margin_risk: Margin debt risk
            adjustment_result: Result từ adjust_prediction_for_cascade

        Returns:
            Trading recommendation
        """
        if crisis_level in [MarginCrisisLevel.NORMAL, MarginCrisisLevel.WARNING]:
            if cascade_phase == "recovery":
                return {
                    'action': 'BUY',
                    'confidence': 'MEDIUM',
                    'reasoning': 'Cascade recovery. Bargain hunting opportunity.',
                    'position_size': 'NORMAL',
                    'entry_timing': 'NOW - Recovery phase',
                    'exit_strategy': 'T+10 to T+20',
                    'stop_loss': 0.05
                }
            else:
                return {
                    'action': 'NORMAL',
                    'confidence': 'NORMAL',
                    'reasoning': 'No margin call risk. Normal trading.',
                    'position_size': 'NORMAL',
                    'entry_timing': 'NORMAL',
                    'exit_strategy': 'NORMAL',
                    'stop_loss': None
                }

        elif crisis_level == MarginCrisisLevel.TRIGGER:
            if margin_risk in ['EXTREME', 'HIGH']:
                return {
                    'action': 'SELL',
                    'confidence': 'HIGH',
                    'reasoning': f'Margin cascade triggered. {margin_risk} margin debt. Exit.',
                    'position_size': 'REDUCE',
                    'entry_timing': 'AVOID',
                    'exit_strategy': 'NOW - Before cascade deepens',
                    'stop_loss': None
                }
            else:
                return {
                    'action': 'HOLD',
                    'confidence': 'MEDIUM',
                    'reasoning': f'Cascade triggered but {margin_risk} margin risk. Monitor.',
                    'position_size': 'REDUCE',
                    'entry_timing': 'WAIT',
                    'exit_strategy': 'If crisis worsens',
                    'stop_loss': 0.07
                }

        elif crisis_level in [MarginCrisisLevel.CASCADE, MarginCrisisLevel.PANIC]:
            if cascade_phase in ["cascade_early", "cascade_middle", "panic"]:
                return {
                    'action': 'AVOID',
                    'confidence': 'EXTREME',
                    'reasoning': 'Active margin cascade. Do not catch falling knife.',
                    'position_size': 'ZERO',
                    'entry_timing': 'WAIT - Until exhaustion',
                    'exit_strategy': 'Cut losses if still holding',
                    'stop_loss': 0.10
                }

            elif cascade_phase in ["cascade_late", "exhaustion"]:
                if margin_risk in ['MINIMAL', 'LOW']:
                    return {
                        'action': 'WATCH',
                        'confidence': 'MEDIUM',
                        'reasoning': f'Cascade nearing end. {margin_risk} risk. Watch for bottom.',
                        'position_size': 'SMALL',
                        'entry_timing': 'WAIT - Confirm exhaustion',
                        'exit_strategy': 'T+5 to T+10 bounce',
                        'stop_loss': 0.05
                    }
                else:
                    return {
                        'action': 'WAIT',
                        'confidence': 'LOW',
                        'reasoning': f'{margin_risk} margin risk. Wait for clear bottom.',
                        'position_size': 'ZERO',
                        'entry_timing': 'WAIT - Full exhaustion + recovery',
                        'exit_strategy': 'N/A',
                        'stop_loss': None
                    }

            else:
                return {
                    'action': 'AVOID',
                    'confidence': 'HIGH',
                    'reasoning': 'Margin crisis ongoing. Stay defensive.',
                    'position_size': 'ZERO',
                    'entry_timing': 'AVOID',
                    'exit_strategy': 'N/A',
                    'stop_loss': None
                }

        else:
            return {
                'action': 'WAIT',
                'confidence': 'LOW',
                'reasoning': 'Uncertain conditions. Stay cautious.',
                'position_size': 'SMALL',
                'entry_timing': 'WAIT',
                'exit_strategy': 'Quick exit if worsens',
                'stop_loss': 0.05
            }

    def start_cascade_tracking(self, trigger_date: datetime, trigger_price: float,
                              crisis_level: MarginCrisisLevel) -> str:
        """
        Bắt đầu tracking một cascade event mới.

        Args:
            trigger_date: Ngày trigger
            trigger_price: VN-Index price tại trigger
            crisis_level: Mức độ khủng hoảng

        Returns:
            cascade_id
        """
        cascade_id = f"cascade_{trigger_date.strftime('%Y%m%d')}"

        self.active_cascade = {
            'cascade_id': cascade_id,
            'trigger_date': trigger_date,
            'trigger_price': trigger_price,
            'crisis_level': crisis_level,
            'status': 'ACTIVE',
            'created_at': datetime.now()
        }

        return cascade_id

    def end_cascade_tracking(self, end_date: datetime, recovery_confirmed: bool = False):
        """
        Kết thúc tracking cascade hiện tại.

        Args:
            end_date: Ngày kết thúc
            recovery_confirmed: Recovery đã được confirm chưa
        """
        if self.active_cascade:
            self.active_cascade['end_date'] = end_date
            self.active_cascade['duration'] = (end_date - self.active_cascade['trigger_date']).days
            self.active_cascade['status'] = 'ENDED'
            self.active_cascade['recovery_confirmed'] = recovery_confirmed

            # Archive cascade for historical learning
            # TODO: Save to database

            # Clear active cascade
            self.active_cascade = None


# Example usage
if __name__ == "__main__":
    handler = MarginCallHandler()

    # Simulate VN-Index prices (declining market)
    dates = pd.date_range(end=datetime.now(), periods=20, freq='D')
    vnindex_prices = pd.Series(
        [1200, 1210, 1205, 1190, 1175, 1160, 1140, 1125, 1110, 1100,
         1095, 1090, 1085, 1088, 1092, 1095, 1100, 1105, 1110, 1115],
        index=dates
    )
    vnindex_prices = vnindex_prices.iloc[::-1]  # Recent first

    # Detect market stress
    crisis_level, details = handler.detect_market_stress(vnindex_prices)
    print(f"Crisis Level: {crisis_level}")
    print(f"Drawdown: {details['drawdown']:.2%}")
    print(f"7-day change: {details['change_7d']:.2%}")

    # Check margin debt for a stock
    ticker = 'HPG'
    margin_risk, margin_ratio, margin_details = handler.check_margin_debt_level(
        ticker=ticker,
        margin_debt_vnd=2_000_000_000_000,  # 2T VND
        market_cap_vnd=100_000_000_000_000   # 100T VND
    )
    print(f"\nMargin Risk ({ticker}): {margin_risk}")
    print(f"Margin Ratio: {margin_ratio:.2%}")

    # Determine cascade phase
    phase = handler.detect_cascade_phase(
        crisis_level=crisis_level,
        days_since_trigger=5,
        price_change_since_trigger=-0.10,
        volume_trend="falling"
    )
    print(f"\nCascade Phase: {phase}")

    # Adjust prediction
    adjustment = handler.adjust_prediction_for_cascade(
        ticker=ticker,
        base_prediction=45000,
        current_price=42000,
        crisis_level=crisis_level,
        cascade_phase=phase,
        margin_risk=margin_risk,
        days_since_trigger=5
    )

    print(f"\nAdjusted Prediction: {adjustment['adjusted_prediction']:,.0f}")
    print(f"Adjustment Factor: {adjustment['adjustment_factor']:.2%}")
    print(f"Reasoning: {adjustment['reasoning']}")
    print(f"Confidence: [{adjustment['confidence_lower']:,.0f}, {adjustment['confidence_upper']:,.0f}]")

    # Get recommendation
    recommendation = handler.generate_defensive_recommendation(
        ticker=ticker,
        crisis_level=crisis_level,
        cascade_phase=phase,
        margin_risk=margin_risk,
        adjustment_result=adjustment
    )

    print(f"\nRecommendation: {recommendation['action']}")
    print(f"Confidence: {recommendation['confidence']}")
    print(f"Reasoning: {recommendation['reasoning']}")
    print(f"Entry: {recommendation['entry_timing']}")

    # Check exhaustion signals
    exhaustion = handler.detect_exhaustion_signals(
        ticker=ticker,
        price_series=pd.Series([42000, 42100, 41900, 41800, 41500])
    )
    print(f"\nExhaustion Score: {exhaustion['exhaustion_score']:.2f}")
    print(f"Signals: {exhaustion['signals']}")
    print(f"Likely Bottom: {exhaustion['likely_bottom']}")
