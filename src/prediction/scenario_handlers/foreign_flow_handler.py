"""
Foreign Flow Handler - Xử lý dòng tiền ngoại

Thị trường VN có giới hạn room ngoại:
- Most stocks: 30% foreign ownership limit
- Some stocks: 49% limit (banks, etc.)

Khi room gần đầy → Ngoại không mua được → Upside limited
Khi ngoại bán ròng mạnh → Sell pressure → Giá giảm
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional


class ForeignFlowHandler:
    """
    Handler for foreign investor flow dynamics

    Key metrics:
    - Foreign ownership % vs limit
    - Foreign net buy/sell (daily, weekly)
    - Room availability
    - Foreign trading patterns
    """

    def __init__(self):
        # Foreign ownership limits by stock
        self.foreign_limits = {
            # Banks: 30%
            'VCB': 0.30, 'BID': 0.30, 'CTG': 0.30, 'MBB': 0.30,
            'TCB': 0.30, 'VPB': 0.30, 'ACB': 0.30, 'HDB': 0.30,

            # Real estate: 49%
            'VHM': 0.49, 'VIC': 0.49, 'NVL': 0.49, 'KDH': 0.49,

            # Manufacturing: 49-100%
            'HPG': 0.49, 'GVR': 0.49, 'MSN': 0.49,

            # Others: 49%
            'VNM': 0.49, 'SAB': 0.49, 'FPT': 0.49, 'MWG': 0.49,
        }

        # Thresholds
        self.ROOM_WARNING_THRESHOLD = 0.90  # 90% full
        self.ROOM_CRITICAL_THRESHOLD = 0.95  # 95% full
        self.SIGNIFICANT_FLOW = 500_000  # 500K shares in 3 days

    def get_foreign_limit(self, ticker: str) -> float:
        """Get foreign ownership limit for ticker"""
        return self.foreign_limits.get(ticker, 0.49)  # Default 49%

    def check_room_status(
        self,
        ticker: str,
        current_foreign_ownership: float
    ) -> Tuple[str, float, Dict]:
        """
        Kiểm tra tình trạng room ngoại

        Args:
            ticker: Stock ticker
            current_foreign_ownership: Current foreign ownership (0-1)

        Returns:
            (status, room_ratio, details)
        """
        foreign_limit = self.get_foreign_limit(ticker)
        room_ratio = current_foreign_ownership / foreign_limit
        room_available = foreign_limit - current_foreign_ownership

        if room_ratio >= 1.0:
            status = "FULL"
            impact = "SEVERE"
            message = f"Room đầy! Ngoại không thể mua thêm"
            prediction_adjustment = -0.03  # -3%

        elif room_ratio >= self.ROOM_CRITICAL_THRESHOLD:
            status = "CRITICAL"
            impact = "HIGH"
            message = f"Room gần đầy ({room_ratio:.1%}), upside bị giới hạn"
            prediction_adjustment = -0.02  # -2%

        elif room_ratio >= self.ROOM_WARNING_THRESHOLD:
            status = "WARNING"
            impact = "MEDIUM"
            message = f"Room ở mức cao ({room_ratio:.1%}), cần theo dõi"
            prediction_adjustment = -0.01  # -1%

        else:
            status = "HEALTHY"
            impact = "LOW"
            message = f"Room còn thoải mái ({room_ratio:.1%})"
            prediction_adjustment = 0.0

        return status, room_ratio, {
            'status': status,
            'impact': impact,
            'message': message,
            'room_ratio': room_ratio,
            'room_available': room_available,
            'foreign_limit': foreign_limit,
            'current_ownership': current_foreign_ownership,
            'prediction_adjustment': prediction_adjustment
        }

    def analyze_foreign_flow(
        self,
        ticker: str,
        flow_data: pd.DataFrame
    ) -> Dict:
        """
        Phân tích dòng tiền ngoại

        Args:
            ticker: Stock ticker
            flow_data: DataFrame with columns ['date', 'buy_volume', 'sell_volume', 'net_volume']

        Returns:
            Analysis dictionary
        """
        # Calculate metrics
        net_1d = flow_data['net_volume'].iloc[-1]
        net_3d = flow_data['net_volume'].tail(3).sum()
        net_5d = flow_data['net_volume'].tail(5).sum()
        net_10d = flow_data['net_volume'].tail(10).sum()

        # Average daily volume
        avg_volume = flow_data['buy_volume'].mean() + flow_data['sell_volume'].mean()

        # Determine flow pattern
        if net_3d > self.SIGNIFICANT_FLOW:
            flow_pattern = "STRONG_INFLOW"
            impact = "POSITIVE"
            message = f"Ngoại mua ròng mạnh: {net_3d:,.0f} cp (3 ngày)"
            prediction_adjustment = +0.015  # +1.5%

        elif net_3d > self.SIGNIFICANT_FLOW * 0.5:
            flow_pattern = "MODERATE_INFLOW"
            impact = "POSITIVE"
            message = f"Ngoại mua ròng: {net_3d:,.0f} cp (3 ngày)"
            prediction_adjustment = +0.008  # +0.8%

        elif net_3d < -self.SIGNIFICANT_FLOW:
            flow_pattern = "STRONG_OUTFLOW"
            impact = "NEGATIVE"
            message = f"Ngoại bán ròng mạnh: {net_3d:,.0f} cp (3 ngày)"
            prediction_adjustment = -0.020  # -2%

        elif net_3d < -self.SIGNIFICANT_FLOW * 0.5:
            flow_pattern = "MODERATE_OUTFLOW"
            impact = "NEGATIVE"
            message = f"Ngoại bán ròng: {net_3d:,.0f} cp (3 ngày)"
            prediction_adjustment = -0.010  # -1%

        else:
            flow_pattern = "NEUTRAL"
            impact = "NEUTRAL"
            message = "Dòng tiền ngoại trung tính"
            prediction_adjustment = 0.0

        # Detect trend
        if net_1d > 0 and net_3d > 0 and net_5d > 0:
            trend = "SUSTAINED_BUYING"
            trend_strength = "STRONG"
        elif net_1d < 0 and net_3d < 0 and net_5d < 0:
            trend = "SUSTAINED_SELLING"
            trend_strength = "STRONG"
        elif abs(net_5d) < avg_volume * 0.1:
            trend = "SIDEWAYS"
            trend_strength = "WEAK"
        else:
            trend = "MIXED"
            trend_strength = "MODERATE"

        return {
            'ticker': ticker,
            'flow_pattern': flow_pattern,
            'impact': impact,
            'message': message,
            'prediction_adjustment': prediction_adjustment,
            'metrics': {
                'net_1d': net_1d,
                'net_3d': net_3d,
                'net_5d': net_5d,
                'net_10d': net_10d
            },
            'trend': trend,
            'trend_strength': trend_strength,
            'avg_daily_volume': avg_volume
        }

    def combined_analysis(
        self,
        ticker: str,
        current_foreign_ownership: float,
        flow_data: pd.DataFrame
    ) -> Dict:
        """
        Phân tích kết hợp room + flow

        Args:
            ticker: Stock ticker
            current_foreign_ownership: Current foreign ownership
            flow_data: Foreign flow data

        Returns:
            Combined analysis
        """
        # Room analysis
        room_status, room_ratio, room_details = self.check_room_status(
            ticker, current_foreign_ownership
        )

        # Flow analysis
        flow_analysis = self.analyze_foreign_flow(ticker, flow_data)

        # Combined interpretation
        combined_adjustment = (
            room_details['prediction_adjustment'] +
            flow_analysis['prediction_adjustment']
        )

        # Special cases
        if room_status == "FULL" and flow_analysis['flow_pattern'] == "STRONG_INFLOW":
            # Ngoại muốn mua nhưng không mua được
            situation = "DEMAND_BLOCKED"
            message = "⚠️ Ngoại muốn mua nhưng room đầy → Giá có thể đình trệ"
            confidence = "HIGH"
            combined_adjustment = -0.04  # -4%

        elif room_status == "FULL" and flow_analysis['flow_pattern'] == "STRONG_OUTFLOW":
            # Room đầy + ngoại bán = rất tiêu cực
            situation = "FULL_ROOM_SELLING"
            message = "🔴 Room đầy + ngoại bán ròng → Rất tiêu cực"
            confidence = "HIGH"
            combined_adjustment = -0.06  # -6%

        elif room_status == "HEALTHY" and flow_analysis['flow_pattern'] == "STRONG_INFLOW":
            # Tình huống lý tưởng
            situation = "IDEAL_BUYING"
            message = "✅ Room thoải mái + ngoại mua ròng → Rất tích cực"
            confidence = "HIGH"
            combined_adjustment = +0.03  # +3%

        elif room_status in ["WARNING", "CRITICAL"] and flow_analysis['flow_pattern'] == "STRONG_INFLOW":
            # Ngoại rush vào trước khi room đầy
            situation = "RUSH_BUYING"
            message = "⚡ Ngoại rush mua trước khi room đầy → Tích cực ngắn hạn"
            confidence = "MEDIUM"
            combined_adjustment = +0.02  # +2%

        else:
            situation = "NORMAL"
            message = f"Room: {room_status}, Flow: {flow_analysis['flow_pattern']}"
            confidence = "MEDIUM"

        return {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'situation': situation,
            'message': message,
            'confidence': confidence,
            'combined_adjustment': combined_adjustment,
            'room_analysis': room_details,
            'flow_analysis': flow_analysis,
            'recommendation': self._generate_recommendation(
                situation, room_ratio, flow_analysis['flow_pattern']
            )
        }

    def _generate_recommendation(
        self,
        situation: str,
        room_ratio: float,
        flow_pattern: str
    ) -> str:
        """Generate trading recommendation"""

        if situation == "IDEAL_BUYING":
            return "✅ MUA - Điều kiện tốt: room thoải mái + ngoại mua mạnh"

        elif situation == "RUSH_BUYING":
            return "⚡ MUA ngắn hạn - Ngoại rush vào, nhưng cẩn thận khi room đầy"

        elif situation == "DEMAND_BLOCKED":
            return "⚠️ NẮM GIỮ/BÁN - Room đầy chặn demand, upside bị giới hạn"

        elif situation == "FULL_ROOM_SELLING":
            return "🔴 BÁN - Room đầy + ngoại bán = downside risk cao"

        elif room_ratio > 0.95:
            return "⚠️ THẬN TRỌNG - Room gần đầy, upside bị giới hạn"

        elif flow_pattern == "STRONG_OUTFLOW":
            return "⚠️ THẬN TRỌNG - Ngoại đang bán ròng mạnh"

        elif flow_pattern == "STRONG_INFLOW":
            return "✅ TÍCH CỰC - Ngoại đang mua ròng mạnh"

        else:
            return "🔵 TRUNG TÍNH - Theo dõi thêm"

    def create_report(self, analysis: Dict) -> str:
        """Tạo báo cáo foreign flow"""

        report = f"""
╔════════════════════════════════════════════════════════════╗
║          FOREIGN FLOW ANALYSIS: {analysis['ticker']:<26} ║
╠════════════════════════════════════════════════════════════╣

📊 TÌNH HUỐNG: {analysis['situation']}
{analysis['message']}

┌──────────────────────────────────────────────────────────┐
│ ROOM STATUS                                              │
├──────────────────────────────────────────────────────────┤
│ Status:        {analysis['room_analysis']['status']:<40} │
│ Room ratio:    {analysis['room_analysis']['room_ratio']:.1%}{' '*(39-len(f"{analysis['room_analysis']['room_ratio']:.1%}"))} │
│ Room left:     {analysis['room_analysis']['room_available']:.2%}{' '*(39-len(f"{analysis['room_analysis']['room_available']:.2%}"))} │
│ Impact:        {analysis['room_analysis']['impact']:<40} │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ FOREIGN FLOW (Net Buy/Sell)                             │
├──────────────────────────────────────────────────────────┤
│ Pattern:       {analysis['flow_analysis']['flow_pattern']:<40} │
│ 1-day:         {analysis['flow_analysis']['metrics']['net_1d']:>10,.0f} shares{' '*(24-len(f"{analysis['flow_analysis']['metrics']['net_1d']:,.0f}"))} │
│ 3-day:         {analysis['flow_analysis']['metrics']['net_3d']:>10,.0f} shares{' '*(24-len(f"{analysis['flow_analysis']['metrics']['net_3d']:,.0f}"))} │
│ 5-day:         {analysis['flow_analysis']['metrics']['net_5d']:>10,.0f} shares{' '*(24-len(f"{analysis['flow_analysis']['metrics']['net_5d']:,.0f}"))} │
│ Trend:         {analysis['flow_analysis']['trend']:<40} │
└──────────────────────────────────────────────────────────┘

💡 RECOMMENDATION:
{analysis['recommendation']}

📈 PREDICTION ADJUSTMENT: {analysis['combined_adjustment']:+.2%}
⭐ CONFIDENCE: {analysis['confidence']}

╚════════════════════════════════════════════════════════════╝
        """
        return report


# Example usage
if __name__ == "__main__":
    handler = ForeignFlowHandler()

    print("="*80)
    print("SCENARIO 1: VHM - Room gần đầy + ngoại mua mạnh")
    print("="*80)

    # Simulate VHM data
    # Room: 48.5% / 49% (99% full!)
    # Foreign buying strong

    # Generate sample flow data
    dates = pd.date_range(end=datetime.now(), periods=10, freq='D')
    flow_data = pd.DataFrame({
        'date': dates,
        'buy_volume': np.random.randint(800_000, 1_200_000, 10),
        'sell_volume': np.random.randint(200_000, 400_000, 10)
    })
    flow_data['net_volume'] = flow_data['buy_volume'] - flow_data['sell_volume']

    analysis = handler.combined_analysis(
        ticker='VHM',
        current_foreign_ownership=0.485,  # 48.5%
        flow_data=flow_data
    )

    print(handler.create_report(analysis))

    print("\n" + "="*80)
    print("SCENARIO 2: VCB - Room đầy + ngoại bán ròng")
    print("="*80)

    # Room: 30% / 30% (100% full!)
    # Foreign selling strong

    flow_data2 = pd.DataFrame({
        'date': dates,
        'buy_volume': np.random.randint(100_000, 300_000, 10),
        'sell_volume': np.random.randint(600_000, 1_000_000, 10)
    })
    flow_data2['net_volume'] = flow_data2['buy_volume'] - flow_data2['sell_volume']

    analysis2 = handler.combined_analysis(
        ticker='VCB',
        current_foreign_ownership=0.30,  # 30% (FULL!)
        flow_data=flow_data2
    )

    print(handler.create_report(analysis2))

    print("\n" + "="*80)
    print("SCENARIO 3: HPG - Room thoải mái + ngoại mua mạnh (IDEAL)")
    print("="*80)

    flow_data3 = pd.DataFrame({
        'date': dates,
        'buy_volume': np.random.randint(900_000, 1_300_000, 10),
        'sell_volume': np.random.randint(200_000, 400_000, 10)
    })
    flow_data3['net_volume'] = flow_data3['buy_volume'] - flow_data3['sell_volume']

    analysis3 = handler.combined_analysis(
        ticker='HPG',
        current_foreign_ownership=0.35,  # 35% / 49% (comfortable)
        flow_data=flow_data3
    )

    print(handler.create_report(analysis3))
