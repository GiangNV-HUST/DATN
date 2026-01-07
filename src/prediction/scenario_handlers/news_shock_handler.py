"""
News Shock Handler - Xử lý tin tức đột ngột

Khi có tin tức quan trọng (earnings, M&A, policy):
1. Detect tin tức từ news API hoặc price action
2. Trigger immediate lightweight retrain
3. Adjust predictions với news sentiment
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple


class NewsShockHandler:
    """
    Handler cho tin tức đột ngột ảnh hưởng giá cổ phiếu

    Scenarios:
    - Positive news: Earnings beat, M&A, partnerships
    - Negative news: Earnings miss, scandals, lawsuits
    - Policy changes: Interest rates, regulations
    """

    def __init__(self):
        self.shock_memory = {}  # Cache recent shocks

    def detect_price_shock(
        self,
        ticker: str,
        current_price: float,
        previous_prices: pd.Series,
        threshold: float = 0.05
    ) -> Tuple[bool, str, float]:
        """
        Phát hiện price shock (thay đổi bất thường)

        Args:
            ticker: Stock ticker
            current_price: Giá hiện tại
            previous_prices: Giá 5-10 ngày trước
            threshold: % thay đổi để coi là shock (default 5%)

        Returns:
            (is_shock, shock_type, magnitude)
        """
        # Calculate typical daily change
        daily_returns = previous_prices.pct_change().dropna()
        avg_change = daily_returns.mean()
        std_change = daily_returns.std()

        # Current change
        last_price = previous_prices.iloc[-1]
        current_change = (current_price - last_price) / last_price

        # Z-score (số lần độ lệch chuẩn)
        if std_change > 0:
            z_score = (current_change - avg_change) / std_change
        else:
            z_score = 0

        # Shock nếu:
        # 1. Thay đổi > threshold (5%)
        # 2. Hoặc z-score > 3 (3 sigma event)
        is_shock = abs(current_change) > threshold or abs(z_score) > 3

        if is_shock:
            shock_type = "positive" if current_change > 0 else "negative"
            magnitude = abs(current_change) * 100

            return True, shock_type, magnitude
        else:
            return False, "none", 0.0

    def detect_consecutive_limit_moves(
        self,
        ticker: str,
        prices: pd.Series,
        days: int = 2
    ) -> Tuple[bool, str]:
        """
        Phát hiện trần/sàn liên tiếp (dấu hiệu tin tức lớn)

        Args:
            ticker: Stock ticker
            prices: Price series
            days: Số ngày liên tiếp

        Returns:
            (has_consecutive_limits, direction)
        """
        # Calculate daily changes
        returns = prices.pct_change()

        # Check for consecutive ~7% moves (gần trần/sàn)
        limit_threshold = 0.065  # 6.5% (gần 7%)

        consecutive_up = 0
        consecutive_down = 0

        for ret in returns.tail(days):
            if ret > limit_threshold:
                consecutive_up += 1
                consecutive_down = 0
            elif ret < -limit_threshold:
                consecutive_down += 1
                consecutive_up = 0
            else:
                consecutive_up = 0
                consecutive_down = 0

        if consecutive_up >= days:
            return True, "up"
        elif consecutive_down >= days:
            return True, "down"
        else:
            return False, "none"

    def estimate_shock_duration(
        self,
        shock_type: str,
        magnitude: float
    ) -> int:
        """
        Ước tính thời gian ảnh hưởng của shock

        Args:
            shock_type: 'positive' or 'negative'
            magnitude: % thay đổi

        Returns:
            Số ngày shock còn ảnh hưởng
        """
        # Heuristic based on magnitude
        if magnitude > 10:
            # Very strong shock: 5-7 ngày
            duration = 7
        elif magnitude > 5:
            # Strong shock: 3-5 ngày
            duration = 5
        elif magnitude > 3:
            # Medium shock: 2-3 ngày
            duration = 3
        else:
            # Weak shock: 1-2 ngày
            duration = 2

        return duration

    def should_trigger_retrain(
        self,
        ticker: str,
        shock_magnitude: float,
        days_since_shock: int
    ) -> Tuple[bool, str]:
        """
        Quyết định có cần emergency retrain không

        Args:
            ticker: Stock ticker
            shock_magnitude: % thay đổi của shock
            days_since_shock: Số ngày từ khi shock xảy ra

        Returns:
            (should_retrain, reason)
        """
        # Retrain ngay nếu:
        # 1. Shock > 5% VÀ trong 2 ngày đầu
        if shock_magnitude > 5 and days_since_shock <= 2:
            return True, f"Major shock ({shock_magnitude:.1f}%) - immediate retrain needed"

        # 2. Shock > 3% VÀ trong ngày đầu
        if shock_magnitude > 3 and days_since_shock == 0:
            return True, f"Significant shock ({shock_magnitude:.1f}%) - immediate retrain needed"

        # 3. Có consecutive limit moves
        # (được check bởi function khác)

        return False, "Shock not severe enough for immediate retrain"

    def adjust_prediction_for_shock(
        self,
        base_prediction: float,
        current_price: float,
        shock_type: str,
        shock_magnitude: float,
        days_since_shock: int
    ) -> Dict:
        """
        Điều chỉnh prediction dựa trên shock (interim solution)

        Đây là giải pháp TẠM THỜI trước khi retrain xong

        Args:
            base_prediction: Prediction từ model cũ
            current_price: Giá hiện tại
            shock_type: 'positive' or 'negative'
            shock_magnitude: % thay đổi
            days_since_shock: Ngày thứ mấy sau shock

        Returns:
            Adjusted prediction với confidence lower
        """
        # Decay factor: ảnh hưởng giảm dần theo ngày
        decay_factor = max(0, 1 - days_since_shock * 0.2)  # Giảm 20%/ngày

        # Estimate momentum continuation
        if shock_type == "positive":
            # Positive shock: Giá có thể tăng thêm
            momentum = shock_magnitude * 0.3 * decay_factor  # 30% momentum
            adjusted_prediction = base_prediction * (1 + momentum / 100)

            # But cap at +7% (trần)
            max_increase = current_price * 1.07
            adjusted_prediction = min(adjusted_prediction, max_increase)

        else:  # negative
            # Negative shock: Giá có thể giảm thêm
            momentum = -shock_magnitude * 0.3 * decay_factor
            adjusted_prediction = base_prediction * (1 + momentum / 100)

            # But cap at -7% (sàn)
            max_decrease = current_price * 0.93
            adjusted_prediction = max(adjusted_prediction, max_decrease)

        # Lower confidence during shock period
        confidence_penalty = shock_magnitude * 10  # 10x magnitude

        return {
            "original_prediction": base_prediction,
            "adjusted_prediction": adjusted_prediction,
            "adjustment": adjusted_prediction - base_prediction,
            "adjustment_percent": ((adjusted_prediction - base_prediction) / base_prediction) * 100,
            "confidence_penalty": confidence_penalty,
            "reason": f"{shock_type} shock (day {days_since_shock}, magnitude {shock_magnitude:.1f}%)",
            "recommendation": "Wait for retrain to complete for better accuracy"
        }

    def create_shock_report(
        self,
        ticker: str,
        shock_data: Dict
    ) -> str:
        """
        Tạo báo cáo về shock event

        Args:
            ticker: Stock ticker
            shock_data: Data về shock

        Returns:
            Formatted report string
        """
        report = f"""
🚨 SHOCK EVENT DETECTED: {ticker}

Shock Type: {shock_data['shock_type'].upper()}
Magnitude: {shock_data['magnitude']:.2f}%
Detected: {shock_data['timestamp']}

Impact Assessment:
- Expected duration: {shock_data['duration']} days
- Model accuracy impact: HIGH
- Current MAPE: {shock_data.get('current_mape', 'N/A')}%

Recommended Actions:
"""

        if shock_data.get('should_retrain', False):
            report += f"""
1. ⚠️ EMERGENCY RETRAIN TRIGGERED
2. ETA: 1-2 hours
3. Meanwhile: Using adjusted predictions (lower confidence)
4. Alert: Sent to monitoring channels
"""
        else:
            report += f"""
1. ✅ Monitoring situation
2. Will retrain in next weekly cycle
3. Predictions adjusted for shock momentum
4. Alert: Logged for review
"""

        return report


# Example usage
if __name__ == "__main__":
    handler = NewsShockHandler()

    # Simulate VCB price shock
    print("="*80)
    print("SCENARIO: VCB Earnings Beat - Positive Shock")
    print("="*80)

    # Previous prices (5 days)
    previous_prices = pd.Series([95000, 95300, 95100, 94800, 95000])

    # Current price after news
    current_price = 101650  # +7% (trần)

    # Detect shock
    is_shock, shock_type, magnitude = handler.detect_price_shock(
        ticker='VCB',
        current_price=current_price,
        previous_prices=previous_prices
    )

    print(f"\n1. Shock Detection:")
    print(f"   Is Shock: {is_shock}")
    print(f"   Type: {shock_type}")
    print(f"   Magnitude: {magnitude:.2f}%")

    # Check if should retrain
    should_retrain, reason = handler.should_trigger_retrain(
        ticker='VCB',
        shock_magnitude=magnitude,
        days_since_shock=0
    )

    print(f"\n2. Retrain Decision:")
    print(f"   Should Retrain: {should_retrain}")
    print(f"   Reason: {reason}")

    # Estimate duration
    duration = handler.estimate_shock_duration(shock_type, magnitude)
    print(f"\n3. Shock Duration:")
    print(f"   Expected duration: {duration} days")

    # Adjust prediction (interim)
    base_prediction = 96200  # Model cũ predict +1.2%
    adjusted = handler.adjust_prediction_for_shock(
        base_prediction=base_prediction,
        current_price=current_price,
        shock_type=shock_type,
        shock_magnitude=magnitude,
        days_since_shock=0
    )

    print(f"\n4. Interim Prediction Adjustment:")
    print(f"   Original: {adjusted['original_prediction']:,.0f}")
    print(f"   Adjusted: {adjusted['adjusted_prediction']:,.0f}")
    print(f"   Adjustment: {adjusted['adjustment']:+,.0f} ({adjusted['adjustment_percent']:+.1f}%)")
    print(f"   Confidence penalty: {adjusted['confidence_penalty']:.1f}%")
    print(f"   Reason: {adjusted['reason']}")

    # Generate report
    shock_data = {
        'shock_type': shock_type,
        'magnitude': magnitude,
        'timestamp': datetime.now().isoformat(),
        'duration': duration,
        'should_retrain': should_retrain,
        'current_mape': 5.8
    }

    print(handler.create_shock_report('VCB', shock_data))
