"""
VN30 Adjustment Handler - Xử lý thay đổi danh mục VN30

VN30 Index adjustment là sự kiện quan trọng đặc thù của thị trường Việt Nam.
Khi một cổ phiếu được thêm vào hoặc loại khỏi danh mục VN30, có dòng tiền khổng lồ
từ các quỹ bị động (passive funds) phải mua/bán để rebalance.

Đặc điểm:
- Xảy ra 2 lần/năm: tháng 6 và tháng 12
- HSX công bố trước ~10-15 ngày so với ngày hiệu lực
- Tác động có thể dự đoán trước (predictable)
- Magnitude lớn: +15-25% (addition), -10-20% (removal)

Phases:
1. Announcement (T-15 to T-10): Thị trường bắt đầu định giá lại
2. Anticipation (T-10 to T-1): Speculators mua trước
3. Rebalancing (T to T+3): Passive funds thực hiện mua/bán
4. Stabilization (T+4 to T+10): Giá điều chỉnh về cân bằng mới
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from enum import Enum


class VN30Event(Enum):
    """Loại sự kiện VN30"""
    ADDITION = "addition"  # Thêm vào VN30
    REMOVAL = "removal"    # Loại khỏi VN30
    NO_EVENT = "no_event"  # Không có sự kiện


class VN30Phase(Enum):
    """Giai đoạn của sự kiện VN30"""
    NORMAL = "normal"                    # Không có sự kiện
    ANNOUNCEMENT = "announcement"        # T-15 đến T-10
    ANTICIPATION = "anticipation"        # T-10 đến T-1
    REBALANCING = "rebalancing"          # T đến T+3
    STABILIZATION = "stabilization"      # T+4 đến T+10
    POST_EVENT = "post_event"            # T+11 trở đi


class VN30AdjustmentHandler:
    """
    Handler cho VN30 index adjustment events.

    Xử lý các kịch bản:
    1. Stock được thêm vào VN30 → Tăng giá mạnh
    2. Stock bị loại khỏi VN30 → Giảm giá
    3. Speculation phase → Giá tăng/giảm trước ngày hiệu lực
    4. Post-rebalancing → Mean reversion
    """

    def __init__(self):
        """Initialize VN30 Adjustment Handler"""
        # Current VN30 constituents (cập nhật định kỳ)
        self.current_vn30 = [
            'VCB', 'VHM', 'VIC', 'VNM', 'HPG', 'GAS', 'MSN', 'TCB',
            'MWG', 'VPB', 'BID', 'CTG', 'SAB', 'PLX', 'MBB', 'VRE',
            'HDB', 'NVL', 'POW', 'FPT', 'SSI', 'STB', 'VJC', 'PDR',
            'TPB', 'GVR', 'KDH', 'ACB', 'BCM', 'VCI'
        ]

        # Known upcoming VN30 adjustments (cần cập nhật từ HSX announcement)
        self.upcoming_adjustments = {
            # Format: {
            #     'effective_date': '2026-06-20',
            #     'additions': ['NEW1', 'NEW2'],
            #     'removals': ['OLD1', 'OLD2']
            # }
        }

        # Historical adjustment impacts (for learning)
        self.historical_impacts = {
            'addition': {
                'announcement_to_effective': 0.18,  # +18% trung bình
                'peak_day': -3,  # Đạt đỉnh T-3
                'post_rebalance_correction': -0.05  # Giảm 5% sau rebalancing
            },
            'removal': {
                'announcement_to_effective': -0.12,  # -12% trung bình
                'trough_day': -1,  # Đáy tại T-1
                'post_rebalance_bounce': 0.03  # Hồi 3% sau rebalancing
            }
        }

        # Passive fund AUM tracking VN30 (ước tính)
        self.passive_aum_vnd = 50_000_000_000_000  # 50 trillion VND

    def check_vn30_event(self, ticker: str, current_date: datetime) -> Tuple[VN30Event, Optional[datetime], Dict]:
        """
        Kiểm tra xem ticker có liên quan đến VN30 event sắp tới không.

        Args:
            ticker: Mã cổ phiếu
            current_date: Ngày hiện tại

        Returns:
            (event_type, effective_date, details)
        """
        # Check upcoming adjustments
        for event_id, event_info in self.upcoming_adjustments.items():
            effective_date = datetime.strptime(event_info['effective_date'], '%Y-%m-%d')

            # Check if ticker in additions
            if ticker in event_info.get('additions', []):
                days_until = (effective_date - current_date).days
                return VN30Event.ADDITION, effective_date, {
                    'days_until_effective': days_until,
                    'announcement_date': event_info.get('announcement_date'),
                    'event_id': event_id
                }

            # Check if ticker in removals
            if ticker in event_info.get('removals', []):
                days_until = (effective_date - current_date).days
                return VN30Event.REMOVAL, effective_date, {
                    'days_until_effective': days_until,
                    'announcement_date': event_info.get('announcement_date'),
                    'event_id': event_id
                }

        return VN30Event.NO_EVENT, None, {}

    def get_event_phase(self, days_until_effective: int) -> VN30Phase:
        """
        Xác định phase hiện tại của VN30 event.

        Args:
            days_until_effective: Số ngày đến ngày hiệu lực (có thể âm nếu đã qua)

        Returns:
            VN30Phase
        """
        if days_until_effective > 10:
            return VN30Phase.ANNOUNCEMENT
        elif days_until_effective > 0:
            return VN30Phase.ANTICIPATION
        elif days_until_effective >= -3:
            return VN30Phase.REBALANCING
        elif days_until_effective >= -10:
            return VN30Phase.STABILIZATION
        elif days_until_effective >= -30:
            return VN30Phase.POST_EVENT
        else:
            return VN30Phase.NORMAL

    def estimate_passive_flow(self, ticker: str, event_type: VN30Event,
                             market_cap_vnd: float, free_float: float = 0.8) -> Dict:
        """
        Ước tính dòng tiền từ passive funds.

        Args:
            ticker: Mã cổ phiếu
            event_type: ADDITION hoặc REMOVAL
            market_cap_vnd: Market cap (VND)
            free_float: Tỷ lệ free float (0-1)

        Returns:
            {
                'estimated_flow_vnd': float,  # Dòng tiền ước tính (VND)
                'estimated_flow_shares': float,  # Số lượng cổ phiếu
                'index_weight': float,  # Tỷ trọng trong VN30 (%)
                'days_to_execute': int  # Số ngày thực hiện
            }
        """
        # Estimate VN30 total market cap (top 30 stocks)
        vn30_total_mcap = 3_000_000_000_000_000  # ~3 quadrillion VND (estimate)

        # Calculate index weight
        index_weight = market_cap_vnd / vn30_total_mcap

        # Passive funds need to buy/sell this percentage of their AUM
        target_allocation = index_weight * self.passive_aum_vnd

        # Flow direction
        if event_type == VN30Event.ADDITION:
            estimated_flow = target_allocation  # Positive (buying)
        elif event_type == VN30Event.REMOVAL:
            estimated_flow = -target_allocation  # Negative (selling)
        else:
            estimated_flow = 0

        # Calculate shares (assuming current price from market cap)
        shares_outstanding = market_cap_vnd / 10000  # Rough estimate
        free_float_shares = shares_outstanding * free_float
        estimated_shares = estimated_flow / (market_cap_vnd / shares_outstanding)

        # Execution timeline (passive funds usually execute over 3-5 days)
        days_to_execute = 4

        return {
            'estimated_flow_vnd': estimated_flow,
            'estimated_flow_shares': estimated_shares,
            'index_weight': index_weight * 100,  # Percentage
            'days_to_execute': days_to_execute,
            'daily_flow_vnd': estimated_flow / days_to_execute,
            'daily_flow_shares': estimated_shares / days_to_execute,
            'pressure_level': self._calculate_pressure_level(estimated_flow, market_cap_vnd)
        }

    def _calculate_pressure_level(self, flow_vnd: float, market_cap: float) -> str:
        """
        Tính mức độ áp lực từ passive flow.

        Args:
            flow_vnd: Dòng tiền (VND), dương = mua, âm = bán
            market_cap: Market cap (VND)

        Returns:
            Pressure level: LOW, MEDIUM, HIGH, EXTREME
        """
        # Calculate flow as % of market cap
        flow_ratio = abs(flow_vnd) / market_cap

        if flow_ratio < 0.01:  # <1% of market cap
            return "LOW"
        elif flow_ratio < 0.03:  # 1-3%
            return "MEDIUM"
        elif flow_ratio < 0.05:  # 3-5%
            return "HIGH"
        else:  # >5%
            return "EXTREME"

    def calculate_price_adjustment(self, ticker: str, event_type: VN30Event,
                                   phase: VN30Phase, days_until_effective: int,
                                   current_price: float, market_cap: float) -> Dict:
        """
        Tính toán adjustment cho prediction dựa trên VN30 event.

        Args:
            ticker: Mã cổ phiếu
            event_type: ADDITION hoặc REMOVAL
            phase: Phase hiện tại
            days_until_effective: Ngày đến effective date
            current_price: Giá hiện tại
            market_cap: Market cap (VND)

        Returns:
            {
                'adjustment_factor': float,  # Multiply prediction by this
                'confidence_adjustment': float,  # Add to confidence interval
                'reasoning': str,
                'expected_target': float,  # Target price
                'risk_level': str
            }
        """
        if event_type == VN30Event.ADDITION:
            return self._calculate_addition_adjustment(
                phase, days_until_effective, current_price, market_cap
            )
        elif event_type == VN30Event.REMOVAL:
            return self._calculate_removal_adjustment(
                phase, days_until_effective, current_price, market_cap
            )
        else:
            return {
                'adjustment_factor': 1.0,
                'confidence_adjustment': 0.0,
                'reasoning': "No VN30 event",
                'expected_target': current_price,
                'risk_level': "NORMAL"
            }

    def _calculate_addition_adjustment(self, phase: VN30Phase, days_until: int,
                                      current_price: float, market_cap: float) -> Dict:
        """Calculate adjustment for VN30 addition"""
        base_gain = self.historical_impacts['addition']['announcement_to_effective']

        if phase == VN30Phase.ANNOUNCEMENT:
            # Early phase: 10-15 days out
            # Market just starting to price in
            progress = (15 - days_until) / 5  # 0.0 to 1.0
            expected_gain = base_gain * 0.3 * progress  # First 30% of gain

            return {
                'adjustment_factor': 1.0 + expected_gain,
                'confidence_adjustment': 0.02,  # Wider interval
                'reasoning': f"VN30 addition announced. Early speculation phase. Expected +{expected_gain*100:.1f}%",
                'expected_target': current_price * (1 + base_gain),
                'risk_level': "MEDIUM"
            }

        elif phase == VN30Phase.ANTICIPATION:
            # Peak speculation: 1-10 days out
            # Most of the gain happens here
            progress = (10 - days_until) / 10  # 0.0 to 1.0
            expected_gain = base_gain * (0.3 + 0.6 * progress)  # 30% → 90% of total gain

            # Peak typically at T-3
            if days_until <= 3:
                expected_gain = base_gain * 0.95  # Near peak
                risk = "HIGH"  # Overheating risk
            else:
                risk = "MEDIUM"

            return {
                'adjustment_factor': 1.0 + expected_gain,
                'confidence_adjustment': 0.04,  # High volatility
                'reasoning': f"VN30 addition in {days_until} days. Strong speculation. Expected +{expected_gain*100:.1f}%",
                'expected_target': current_price * (1 + base_gain),
                'risk_level': risk
            }

        elif phase == VN30Phase.REBALANCING:
            # Rebalancing phase: effective date to T+3
            # Passive funds executing, but price may correct
            days_since = abs(days_until)
            correction = self.historical_impacts['addition']['post_rebalance_correction']

            # Peak gain achieved, now correcting
            if days_since == 0:  # Effective date
                expected_move = correction * 0.3  # Start of correction
            else:
                expected_move = correction * min(1.0, days_since / 3)

            return {
                'adjustment_factor': 1.0 + expected_move,
                'confidence_adjustment': 0.03,
                'reasoning': f"VN30 rebalancing day {days_since}. Post-peak correction. Expected {expected_move*100:+.1f}%",
                'expected_target': current_price * (1 + base_gain + correction),
                'risk_level': "MEDIUM"
            }

        elif phase == VN30Phase.STABILIZATION:
            # Stabilization: T+4 to T+10
            # Finding new equilibrium
            days_since = abs(days_until)
            progress = (days_since - 4) / 7  # 0.0 to 1.0

            return {
                'adjustment_factor': 1.0,  # Neutral
                'confidence_adjustment': 0.02 * (1 - progress),  # Narrowing
                'reasoning': f"Post-rebalancing stabilization (day {days_since}). Finding new equilibrium.",
                'expected_target': current_price,
                'risk_level': "LOW"
            }

        else:  # POST_EVENT or NORMAL
            return {
                'adjustment_factor': 1.0,
                'confidence_adjustment': 0.0,
                'reasoning': "VN30 event completed. Back to normal.",
                'expected_target': current_price,
                'risk_level': "NORMAL"
            }

    def _calculate_removal_adjustment(self, phase: VN30Phase, days_until: int,
                                     current_price: float, market_cap: float) -> Dict:
        """Calculate adjustment for VN30 removal"""
        base_loss = self.historical_impacts['removal']['announcement_to_effective']

        if phase == VN30Phase.ANNOUNCEMENT:
            # Early sell-off
            progress = (15 - days_until) / 5
            expected_loss = base_loss * 0.4 * progress  # First 40% of loss (faster than addition)

            return {
                'adjustment_factor': 1.0 + expected_loss,  # Negative loss
                'confidence_adjustment': 0.03,
                'reasoning': f"VN30 removal announced. Early sell-off. Expected {expected_loss*100:.1f}%",
                'expected_target': current_price * (1 + base_loss),
                'risk_level': "HIGH"
            }

        elif phase == VN30Phase.ANTICIPATION:
            # Continued selling pressure
            progress = (10 - days_until) / 10
            expected_loss = base_loss * (0.4 + 0.5 * progress)  # 40% → 90%

            # Trough typically at T-1
            if days_until <= 1:
                expected_loss = base_loss * 0.95
                risk = "EXTREME"
            else:
                risk = "HIGH"

            return {
                'adjustment_factor': 1.0 + expected_loss,
                'confidence_adjustment': 0.05,
                'reasoning': f"VN30 removal in {days_until} days. Heavy selling. Expected {expected_loss*100:.1f}%",
                'expected_target': current_price * (1 + base_loss),
                'risk_level': risk
            }

        elif phase == VN30Phase.REBALANCING:
            # Passive funds dumping, but bargain hunters appear
            days_since = abs(days_until)
            bounce = self.historical_impacts['removal']['post_rebalance_bounce']

            if days_since == 0:
                expected_move = bounce * 0.2
            else:
                expected_move = bounce * min(1.0, days_since / 3)

            return {
                'adjustment_factor': 1.0 + expected_move,
                'confidence_adjustment': 0.04,
                'reasoning': f"VN30 removal rebalancing day {days_since}. Bargain hunting. Expected {expected_move*100:+.1f}%",
                'expected_target': current_price * (1 + base_loss + bounce),
                'risk_level': "MEDIUM"
            }

        elif phase == VN30Phase.STABILIZATION:
            # Stabilizing at new level
            days_since = abs(days_until)
            progress = (days_since - 4) / 7

            return {
                'adjustment_factor': 1.0,
                'confidence_adjustment': 0.02 * (1 - progress),
                'reasoning': f"Post-removal stabilization (day {days_since}). Stabilizing.",
                'expected_target': current_price,
                'risk_level': "LOW"
            }

        else:
            return {
                'adjustment_factor': 1.0,
                'confidence_adjustment': 0.0,
                'reasoning': "VN30 event completed.",
                'expected_target': current_price,
                'risk_level': "NORMAL"
            }

    def generate_recommendation(self, ticker: str, event_type: VN30Event,
                               phase: VN30Phase, days_until: int,
                               adjustment_result: Dict) -> Dict:
        """
        Generate trading recommendation based on VN30 event.

        Returns:
            {
                'action': str,  # BUY, SELL, HOLD, WAIT
                'confidence': str,  # LOW, MEDIUM, HIGH
                'reasoning': str,
                'entry_timing': str,
                'exit_timing': str,
                'stop_loss': float,
                'take_profit': float
            }
        """
        if event_type == VN30Event.ADDITION:
            return self._recommend_addition(phase, days_until, adjustment_result)
        elif event_type == VN30Event.REMOVAL:
            return self._recommend_removal(phase, days_until, adjustment_result)
        else:
            return {
                'action': 'NORMAL',
                'confidence': 'N/A',
                'reasoning': 'No VN30 event',
                'entry_timing': 'N/A',
                'exit_timing': 'N/A',
                'stop_loss': None,
                'take_profit': None
            }

    def _recommend_addition(self, phase: VN30Phase, days_until: int,
                           adjustment: Dict) -> Dict:
        """Recommend for addition event"""
        if phase == VN30Phase.ANNOUNCEMENT:
            if days_until > 12:
                return {
                    'action': 'BUY',
                    'confidence': 'HIGH',
                    'reasoning': 'Early entry for VN30 addition. Best risk/reward.',
                    'entry_timing': 'NOW - Early speculation phase',
                    'exit_timing': 'T-3 to T-1 (before effective date)',
                    'stop_loss': 0.05,  # -5%
                    'take_profit': 0.15  # +15%
                }
            else:
                return {
                    'action': 'BUY',
                    'confidence': 'MEDIUM',
                    'reasoning': 'Still good entry, but some gain already priced in.',
                    'entry_timing': 'NOW - Late announcement phase',
                    'exit_timing': 'T-2 to T (effective date)',
                    'stop_loss': 0.05,
                    'take_profit': 0.12
                }

        elif phase == VN30Phase.ANTICIPATION:
            if days_until >= 5:
                return {
                    'action': 'BUY',
                    'confidence': 'MEDIUM',
                    'reasoning': 'Momentum still strong, but risk increasing.',
                    'entry_timing': 'NOW - Mid speculation',
                    'exit_timing': 'T-1 to T+1',
                    'stop_loss': 0.06,
                    'take_profit': 0.08
                }
            elif days_until >= 2:
                return {
                    'action': 'HOLD',
                    'confidence': 'LOW',
                    'reasoning': 'Near peak. Risk/reward not favorable for new entry.',
                    'entry_timing': 'AVOID - Too late',
                    'exit_timing': 'T to T+1 (take profit)',
                    'stop_loss': 0.07,
                    'take_profit': 0.05
                }
            else:
                return {
                    'action': 'SELL',
                    'confidence': 'HIGH',
                    'reasoning': 'Peak imminent. Lock in profits.',
                    'entry_timing': 'N/A',
                    'exit_timing': 'NOW - Before correction',
                    'stop_loss': None,
                    'take_profit': None
                }

        elif phase == VN30Phase.REBALANCING:
            return {
                'action': 'SELL',
                'confidence': 'MEDIUM',
                'reasoning': 'Post-peak correction likely. Exit if not already.',
                'entry_timing': 'WAIT - Let correction finish',
                'exit_timing': 'NOW',
                'stop_loss': None,
                'take_profit': None
            }

        else:  # STABILIZATION or later
            return {
                'action': 'WAIT',
                'confidence': 'LOW',
                'reasoning': 'Event over. Wait for new opportunity.',
                'entry_timing': 'WAIT - Event completed',
                'exit_timing': 'N/A',
                'stop_loss': None,
                'take_profit': None
            }

    def _recommend_removal(self, phase: VN30Phase, days_until: int,
                          adjustment: Dict) -> Dict:
        """Recommend for removal event"""
        if phase == VN30Phase.ANNOUNCEMENT:
            return {
                'action': 'SELL',
                'confidence': 'HIGH',
                'reasoning': 'VN30 removal announced. Exit before heavy selling.',
                'entry_timing': 'AVOID - Downtrend starting',
                'exit_timing': 'NOW - Before further decline',
                'stop_loss': None,
                'take_profit': None
            }

        elif phase == VN30Phase.ANTICIPATION:
            if days_until > 2:
                return {
                    'action': 'WAIT',
                    'confidence': 'MEDIUM',
                    'reasoning': 'Continued selling pressure. Wait for trough.',
                    'entry_timing': 'WAIT - Until T-1 or T',
                    'exit_timing': 'N/A',
                    'stop_loss': None,
                    'take_profit': None
                }
            else:
                return {
                    'action': 'BUY',
                    'confidence': 'MEDIUM',
                    'reasoning': 'Near trough. Bargain hunting opportunity.',
                    'entry_timing': 'NOW - Near trough (T-1)',
                    'exit_timing': 'T+3 to T+7 (bounce)',
                    'stop_loss': 0.05,
                    'take_profit': 0.05
                }

        elif phase == VN30Phase.REBALANCING:
            days_since = abs(days_until)
            if days_since <= 1:
                return {
                    'action': 'BUY',
                    'confidence': 'HIGH',
                    'reasoning': 'Effective date. Passive selling complete soon.',
                    'entry_timing': 'NOW - Bottom fishing',
                    'exit_timing': 'T+5 to T+10',
                    'stop_loss': 0.05,
                    'take_profit': 0.08
                }
            else:
                return {
                    'action': 'HOLD',
                    'confidence': 'MEDIUM',
                    'reasoning': 'Bounce in progress. Hold for more upside.',
                    'entry_timing': 'LATE - Bounce started',
                    'exit_timing': 'T+7 to T+10',
                    'stop_loss': 0.04,
                    'take_profit': 0.05
                }

        else:  # STABILIZATION or later
            return {
                'action': 'WAIT',
                'confidence': 'LOW',
                'reasoning': 'Event over. Back to normal.',
                'entry_timing': 'NORMAL - No special timing',
                'exit_timing': 'N/A',
                'stop_loss': None,
                'take_profit': None
            }

    def add_adjustment_event(self, effective_date: str, announcement_date: str,
                            additions: List[str], removals: List[str]) -> str:
        """
        Add a new VN30 adjustment event (from HSX announcement).

        Args:
            effective_date: Ngày hiệu lực (YYYY-MM-DD)
            announcement_date: Ngày công bố (YYYY-MM-DD)
            additions: List tickers được thêm vào
            removals: List tickers bị loại khỏi

        Returns:
            event_id
        """
        event_id = f"vn30_adj_{effective_date}"

        self.upcoming_adjustments[event_id] = {
            'effective_date': effective_date,
            'announcement_date': announcement_date,
            'additions': additions,
            'removals': removals,
            'created_at': datetime.now().isoformat()
        }

        # Update current VN30 list
        for ticker in additions:
            if ticker not in self.current_vn30:
                self.current_vn30.append(ticker)

        for ticker in removals:
            if ticker in self.current_vn30:
                self.current_vn30.remove(ticker)

        return event_id


# Example usage
if __name__ == "__main__":
    handler = VN30AdjustmentHandler()

    # Add an example event
    handler.add_adjustment_event(
        effective_date="2026-06-20",
        announcement_date="2026-06-05",
        additions=['DGC', 'VGC'],  # Example
        removals=['BCM', 'VCI']
    )

    # Check event for a stock
    current_date = datetime(2026, 6, 10)  # 10 days before effective
    event_type, effective_date, details = handler.check_vn30_event('DGC', current_date)

    print(f"Event: {event_type}")
    print(f"Days until: {details.get('days_until_effective')}")

    # Get phase
    phase = handler.get_event_phase(details['days_until_effective'])
    print(f"Phase: {phase}")

    # Calculate adjustment
    adjustment = handler.calculate_price_adjustment(
        ticker='DGC',
        event_type=event_type,
        phase=phase,
        days_until_effective=details['days_until_effective'],
        current_price=50000,
        market_cap=10_000_000_000_000  # 10T VND
    )

    print(f"\nAdjustment: {adjustment['adjustment_factor']:.2%}")
    print(f"Reasoning: {adjustment['reasoning']}")
    print(f"Target: {adjustment['expected_target']:,.0f}")

    # Get recommendation
    recommendation = handler.generate_recommendation('DGC', event_type, phase,
                                                    details['days_until_effective'],
                                                    adjustment)
    print(f"\nRecommendation: {recommendation['action']}")
    print(f"Confidence: {recommendation['confidence']}")
    print(f"Entry: {recommendation['entry_timing']}")
    print(f"Exit: {recommendation['exit_timing']}")
