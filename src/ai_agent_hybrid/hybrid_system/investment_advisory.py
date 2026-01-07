"""
Investment Advisory Module

Implements portfolio allocation and investment recommendations
as required in Use Case 9 (Tư vấn đầu tư).

Features:
- Risk profiling
- Portfolio allocation strategies
- Stock selection based on investment goals
- Diversification analysis
- Rebalancing recommendations

Author: Enhanced by AI Assistant
Date: 2026-01-06
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RiskTolerance(Enum):
    """Risk tolerance levels"""
    CONSERVATIVE = "conservative"  # Bảo thủ
    MODERATE = "moderate"  # Cân bằng
    AGGRESSIVE = "aggressive"  # Tích cực


class InvestmentHorizon(Enum):
    """Investment time horizon"""
    SHORT_TERM = "short"  # < 1 year
    MEDIUM_TERM = "medium"  # 1-3 years
    LONG_TERM = "long"  # > 3 years


@dataclass
class InvestorProfile:
    """Investor profile for personalized recommendations"""
    capital: float  # Số vốn đầu tư (VND)
    risk_tolerance: RiskTolerance
    investment_horizon: InvestmentHorizon
    monthly_investment: float = 0  # Đầu tư định kỳ hàng tháng
    existing_holdings: List[Dict] = None  # Danh mục hiện tại
    sectors_to_avoid: List[str] = None  # Ngành tránh
    preferred_sectors: List[str] = None  # Ngành ưu tiên


@dataclass
class PortfolioAllocation:
    """Portfolio allocation recommendation"""
    stocks: List[Dict]  # List of {ticker, shares, amount, weight, rationale}
    total_invested: float
    cash_reserve: float
    expected_return: float  # % per year
    risk_score: float  # 0-10
    diversification_score: float  # 0-10
    recommendations: List[str]  # List of advice


class InvestmentAdvisor:
    """
    Investment Advisory Engine

    Provides personalized stock recommendations and portfolio allocation
    based on investor profile and market conditions.
    """

    def __init__(self, db_client):
        """
        Initialize advisor with database client

        Args:
            db_client: DatabaseTools instance
        """
        self.db = db_client

        # Allocation strategies by risk tolerance
        self.allocation_strategies = {
            RiskTolerance.CONSERVATIVE: {
                "large_cap_weight": 0.70,  # 70% large cap
                "mid_cap_weight": 0.20,  # 20% mid cap
                "small_cap_weight": 0.10,  # 10% small cap
                "min_stocks": 8,
                "max_stocks": 12,
                "max_single_stock": 0.15,  # Max 15% per stock
                "preferred_sectors": ["Ngân hàng", "Bảo hiểm", "Tiện ích"],
                "min_pe": 5,
                "max_pe": 15,
                "min_roe": 12,
                "min_current_ratio": 1.5,
            },
            RiskTolerance.MODERATE: {
                "large_cap_weight": 0.50,
                "mid_cap_weight": 0.35,
                "small_cap_weight": 0.15,
                "min_stocks": 6,
                "max_stocks": 10,
                "max_single_stock": 0.20,  # Max 20% per stock
                "preferred_sectors": ["Ngân hàng", "Bất động sản", "Công nghệ", "Tiêu dùng"],
                "min_pe": 0,
                "max_pe": 20,
                "min_roe": 10,
                "min_current_ratio": 1.2,
            },
            RiskTolerance.AGGRESSIVE: {
                "large_cap_weight": 0.30,
                "mid_cap_weight": 0.40,
                "small_cap_weight": 0.30,
                "min_stocks": 5,
                "max_stocks": 8,
                "max_single_stock": 0.25,  # Max 25% per stock
                "preferred_sectors": ["Công nghệ", "Bất động sản", "Chứng khoán", "Năng lượng"],
                "min_pe": 0,
                "max_pe": 30,
                "min_roe": 8,
                "min_current_ratio": 1.0,
            }
        }

    def create_investment_plan(
        self,
        profile: InvestorProfile
    ) -> PortfolioAllocation:
        """
        Create comprehensive investment plan

        Args:
            profile: Investor profile

        Returns:
            PortfolioAllocation with recommended stocks and allocation
        """
        logger.info(f"Creating investment plan for {profile.capital:,.0f} VND, {profile.risk_tolerance.value} risk")

        # Get allocation strategy
        strategy = self.allocation_strategies[profile.risk_tolerance]

        # Reserve 10-20% cash depending on risk tolerance
        cash_reserve_pct = 0.20 if profile.risk_tolerance == RiskTolerance.CONSERVATIVE else \
                           0.15 if profile.risk_tolerance == RiskTolerance.MODERATE else 0.10

        cash_reserve = profile.capital * cash_reserve_pct
        investable_capital = profile.capital - cash_reserve

        # Find suitable stocks
        candidate_stocks = self._find_suitable_stocks(profile, strategy)

        if not candidate_stocks:
            logger.warning("No suitable stocks found for criteria")
            return PortfolioAllocation(
                stocks=[],
                total_invested=0,
                cash_reserve=profile.capital,
                expected_return=0,
                risk_score=0,
                diversification_score=0,
                recommendations=["Không tìm thấy cổ phiếu phù hợp với tiêu chí. Vui lòng điều chỉnh yêu cầu."]
            )

        # Allocate capital to stocks
        allocated_stocks = self._allocate_capital(
            candidate_stocks,
            investable_capital,
            strategy
        )

        # Calculate metrics
        total_invested = sum(s['amount'] for s in allocated_stocks)
        expected_return = self._estimate_expected_return(allocated_stocks)
        risk_score = self._calculate_risk_score(allocated_stocks, profile.risk_tolerance)
        diversification_score = self._calculate_diversification_score(allocated_stocks)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            allocated_stocks,
            profile,
            expected_return,
            risk_score,
            diversification_score
        )

        return PortfolioAllocation(
            stocks=allocated_stocks,
            total_invested=total_invested,
            cash_reserve=profile.capital - total_invested,
            expected_return=expected_return,
            risk_score=risk_score,
            diversification_score=diversification_score,
            recommendations=recommendations
        )

    def _find_suitable_stocks(
        self,
        profile: InvestorProfile,
        strategy: Dict
    ) -> List[Dict]:
        """Find stocks matching investment criteria"""

        # Build screening criteria
        criteria = {
            "pe_below": strategy["max_pe"],
            "roe_above": strategy["min_roe"],
            "current_ratio_above": strategy["min_current_ratio"],
            "rsi_above": 30,  # Not oversold
            "rsi_below": 70,  # Not overbought
            "limit": 50  # Get top 50 candidates
        }

        if strategy["min_pe"] > 0:
            criteria["pe_above"] = strategy["min_pe"]

        # Search stocks
        stocks = self.db.search_stocks_by_criteria(criteria)

        if not stocks:
            logger.warning("No stocks found matching criteria")
            return []

        # Enrich with company info and score
        enriched_stocks = []
        for stock in stocks:
            # Get company info for sector filtering
            company_info = self.db.get_company_info(stock['ticker'])

            if company_info:
                stock['sector'] = company_info.get('industry', 'Unknown')
                stock['company_name'] = company_info.get('company_name', stock['ticker'])

                # Filter by sector preferences
                if profile.sectors_to_avoid and stock['sector'] in profile.sectors_to_avoid:
                    continue

                # Score the stock
                stock['score'] = self._score_stock(stock, strategy, profile)
                enriched_stocks.append(stock)

        # Sort by score descending
        enriched_stocks.sort(key=lambda x: x['score'], reverse=True)

        logger.info(f"Found {len(enriched_stocks)} suitable stocks after filtering")
        return enriched_stocks

    def _score_stock(self, stock: Dict, strategy: Dict, profile: InvestorProfile) -> float:
        """
        Score a stock based on multiple factors

        Returns:
            float: Score 0-100
        """
        score = 50.0  # Base score

        # ROE scoring (higher is better)
        if stock.get('roe'):
            if stock['roe'] > 20:
                score += 15
            elif stock['roe'] > 15:
                score += 10
            elif stock['roe'] > 10:
                score += 5

        # PE scoring (lower is better, but not too low)
        if stock.get('pe'):
            if 8 < stock['pe'] < 15:
                score += 10
            elif 5 < stock['pe'] <= 8:
                score += 5
            elif stock['pe'] > 25:
                score -= 5

        # PB scoring (lower is better)
        if stock.get('pb'):
            if stock['pb'] < 1.0:
                score += 10
            elif stock['pb'] < 2.0:
                score += 5

        # Debt/Equity scoring (lower is better)
        if stock.get('debt_equity'):
            if stock['debt_equity'] < 0.5:
                score += 10
            elif stock['debt_equity'] < 1.0:
                score += 5
            elif stock['debt_equity'] > 2.0:
                score -= 10

        # RSI scoring (middle is best)
        if stock.get('rsi'):
            if 40 <= stock['rsi'] <= 60:
                score += 10
            elif 30 <= stock['rsi'] < 40 or 60 < stock['rsi'] <= 70:
                score += 5

        # Sector preference bonus
        if profile.preferred_sectors and stock.get('sector') in profile.preferred_sectors:
            score += 15

        # Strategy sector preference
        if stock.get('sector') in strategy['preferred_sectors']:
            score += 10

        return min(100, max(0, score))

    def _allocate_capital(
        self,
        candidate_stocks: List[Dict],
        capital: float,
        strategy: Dict
    ) -> List[Dict]:
        """
        Allocate capital to stocks based on strategy

        Returns:
            List of stocks with allocation details
        """
        num_stocks = min(strategy["max_stocks"], len(candidate_stocks))
        num_stocks = max(strategy["min_stocks"], num_stocks)

        if len(candidate_stocks) < num_stocks:
            num_stocks = len(candidate_stocks)

        # Select top stocks
        selected_stocks = candidate_stocks[:num_stocks]

        # Calculate weights based on scores (score-weighted allocation)
        total_score = sum(s['score'] for s in selected_stocks)

        allocated = []
        remaining_capital = capital

        for i, stock in enumerate(selected_stocks):
            # Weight based on score
            base_weight = (stock['score'] / total_score)

            # Cap at max single stock weight
            weight = min(base_weight, strategy["max_single_stock"])

            # Calculate amount
            if i == len(selected_stocks) - 1:
                # Last stock gets remaining capital
                amount = remaining_capital
            else:
                amount = capital * weight

            # Calculate shares (round down to lot size 100)
            price = stock['close']
            shares = int(amount / price / 100) * 100

            # Actual invested amount
            actual_amount = shares * price

            if shares > 0:
                # Rationale
                rationale = self._generate_stock_rationale(stock)

                allocated.append({
                    "ticker": stock['ticker'],
                    "company_name": stock.get('company_name', stock['ticker']),
                    "sector": stock.get('sector', 'Unknown'),
                    "price": price,
                    "shares": shares,
                    "amount": actual_amount,
                    "weight": actual_amount / capital,
                    "score": stock['score'],
                    "rationale": rationale,
                    # Metrics for display
                    "pe": stock.get('pe'),
                    "pb": stock.get('pb'),
                    "roe": stock.get('roe'),
                    "rsi": stock.get('rsi'),
                })

                remaining_capital -= actual_amount

        return allocated

    def _generate_stock_rationale(self, stock: Dict) -> str:
        """Generate rationale for why this stock was selected"""
        reasons = []

        if stock.get('roe') and stock['roe'] > 15:
            reasons.append(f"ROE cao ({stock['roe']:.1f}%)")

        if stock.get('pe') and 5 < stock['pe'] < 15:
            reasons.append(f"PE hợp lý ({stock['pe']:.1f})")

        if stock.get('pb') and stock['pb'] < 1.5:
            reasons.append(f"PB thấp ({stock['pb']:.2f})")

        if stock.get('debt_equity') and stock['debt_equity'] < 1.0:
            reasons.append(f"Nợ thấp (D/E: {stock['debt_equity']:.2f})")

        if stock.get('rsi') and 40 <= stock['rsi'] <= 60:
            reasons.append("RSI ở vùng trung lập")

        if not reasons:
            reasons.append("Cổ phiếu ổn định")

        return "; ".join(reasons)

    def _estimate_expected_return(self, stocks: List[Dict]) -> float:
        """
        Estimate expected annual return based on historical metrics

        Simple estimate based on average ROE
        """
        if not stocks:
            return 0.0

        # Weight by allocation
        total_weight = sum(s['weight'] for s in stocks)

        weighted_roe = 0
        for stock in stocks:
            if stock.get('roe'):
                weighted_roe += stock['roe'] * (stock['weight'] / total_weight)

        # Expected return ~= ROE * 0.7 (conservative estimate)
        expected_return = weighted_roe * 0.7

        return expected_return

    def _calculate_risk_score(self, stocks: List[Dict], risk_tolerance: RiskTolerance) -> float:
        """Calculate risk score (0-10, higher = more risky)"""
        if not stocks:
            return 0.0

        risk_factors = 0
        count = 0

        for stock in stocks:
            stock_risk = 5.0  # Base risk

            # High debt increases risk
            if stock.get('debt_equity'):
                if stock['debt_equity'] > 2.0:
                    stock_risk += 2
                elif stock['debt_equity'] > 1.0:
                    stock_risk += 1
                elif stock['debt_equity'] < 0.5:
                    stock_risk -= 1

            # High PE might indicate overvaluation
            if stock.get('pe'):
                if stock['pe'] > 25:
                    stock_risk += 1.5
                elif stock['pe'] < 8:
                    stock_risk += 0.5  # Too low might be risky too

            # RSI extremes
            if stock.get('rsi'):
                if stock['rsi'] > 70 or stock['rsi'] < 30:
                    stock_risk += 1

            risk_factors += stock_risk
            count += 1

        avg_risk = risk_factors / count if count > 0 else 5.0

        # Adjust based on risk tolerance target
        if risk_tolerance == RiskTolerance.CONSERVATIVE:
            # Conservative should be low risk (3-5)
            return min(10, avg_risk)
        elif risk_tolerance == RiskTolerance.AGGRESSIVE:
            # Aggressive can be higher risk (6-8)
            return min(10, avg_risk + 1)
        else:
            return min(10, avg_risk)

    def _calculate_diversification_score(self, stocks: List[Dict]) -> float:
        """Calculate diversification score (0-10, higher = more diversified)"""
        if not stocks:
            return 0.0

        score = 0.0

        # Number of stocks (more is better, up to limit)
        num_stocks = len(stocks)
        if num_stocks >= 10:
            score += 4.0
        elif num_stocks >= 7:
            score += 3.0
        elif num_stocks >= 5:
            score += 2.0
        else:
            score += 1.0

        # Sector diversity
        sectors = set(s.get('sector', 'Unknown') for s in stocks)
        num_sectors = len(sectors)
        if num_sectors >= 5:
            score += 3.0
        elif num_sectors >= 4:
            score += 2.5
        elif num_sectors >= 3:
            score += 2.0
        else:
            score += 1.0

        # Weight concentration (more even distribution is better)
        weights = [s['weight'] for s in stocks]
        max_weight = max(weights) if weights else 0
        if max_weight <= 0.15:
            score += 3.0
        elif max_weight <= 0.20:
            score += 2.0
        else:
            score += 1.0

        return min(10.0, score)

    def _generate_recommendations(
        self,
        stocks: List[Dict],
        profile: InvestorProfile,
        expected_return: float,
        risk_score: float,
        diversification_score: float
    ) -> List[str]:
        """Generate investment recommendations"""
        recs = []

        # Summary
        recs.append(
            f"💼 Danh mục đề xuất với {len(stocks)} cổ phiếu, "
            f"kỳ vọng lợi nhuận {expected_return:.1f}%/năm"
        )

        # Risk assessment
        if risk_score <= 4:
            recs.append("✅ Danh mục có mức rủi ro thấp, phù hợp với đầu tư dài hạn")
        elif risk_score <= 7:
            recs.append("⚠️ Danh mục có mức rủi ro trung bình, cần theo dõi định kỳ")
        else:
            recs.append("🔴 Danh mục có mức rủi ro cao, phù hợp với nhà đầu tư chấp nhận rủi ro")

        # Diversification
        if diversification_score >= 8:
            recs.append("✅ Danh mục được phân tán tốt giữa các ngành")
        elif diversification_score >= 6:
            recs.append("⚠️ Nên cân nhắc tăng thêm phân tán giữa các ngành")
        else:
            recs.append("🔴 Danh mục tập trung, rủi ro cao nếu ngành gặp khó khăn")

        # Strategy recommendations
        if profile.risk_tolerance == RiskTolerance.CONSERVATIVE:
            recs.append("📊 Chiến lược bảo thủ: Ưu tiên cổ phiếu blue-chip, cổ tức ổn định")
            recs.append("💡 Nên giữ ít nhất 20% tiền mặt để đối phó biến động thị trường")
        elif profile.risk_tolerance == RiskTolerance.AGGRESSIVE:
            recs.append("🚀 Chiến lược tích cực: Tập trung cổ phiếu tăng trưởng cao")
            recs.append("💡 Cần theo dõi sát sao và sẵn sàng cắt lỗ nếu cần")
        else:
            recs.append("⚖️ Chiến lược cân bằng: Kết hợp giữa tăng trưởng và ổn định")
            recs.append("💡 Rà soát danh mục mỗi quý để điều chỉnh phù hợp")

        # Entry strategy
        if profile.investment_horizon == InvestmentHorizon.LONG_TERM:
            recs.append("📅 Chiến lược mua: Có thể mua dần theo định kỳ (DCA)")
        else:
            recs.append("📅 Chiến lược mua: Theo dõi kỹ điểm vào, nên mua khi thị trường điều chỉnh")

        # Monitoring
        recs.append("🔍 Theo dõi: Kiểm tra danh mục ít nhất mỗi tháng")
        recs.append("🎯 Mục tiêu chốt lời: +15-20% (điều chỉnh theo thị trường)")
        recs.append("🛑 Ngưỡng cắt lỗ: -10% (cần xem xét lại nếu giảm quá mức)")

        return recs
