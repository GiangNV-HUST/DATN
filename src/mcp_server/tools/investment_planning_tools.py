"""
Investment Planning Tools for MCP Server
Handles portfolio allocation and investment recommendations
"""

import asyncio
from typing import Dict, Any, List, Optional
import json


async def gather_investment_profile(
    goals: str = "growth",
    risk_tolerance: str = "moderate",
    timeframe: str = "medium-term",
    capital: float = 100_000_000
) -> Dict[str, Any]:
    """
    Gather user investment profile information

    Args:
        goals: Investment goals (growth, income, preservation, balanced)
        risk_tolerance: Risk tolerance (conservative, moderate, aggressive)
        timeframe: Investment timeframe (short-term, medium-term, long-term)
        capital: Capital to invest in VND

    Returns:
        Dict containing structured investment profile
    """
    profile = {
        "goals": goals.lower(),
        "risk_tolerance": risk_tolerance.lower(),
        "timeframe": timeframe.lower(),
        "capital": capital,
        "recommendations": {}
    }

    # Define allocation strategy based on profile
    if profile["risk_tolerance"] == "conservative":
        profile["recommendations"]["equity_allocation"] = "30-40%"
        profile["recommendations"]["bond_allocation"] = "50-60%"
        profile["recommendations"]["cash_allocation"] = "10-20%"
    elif profile["risk_tolerance"] == "moderate":
        profile["recommendations"]["equity_allocation"] = "50-60%"
        profile["recommendations"]["bond_allocation"] = "30-40%"
        profile["recommendations"]["cash_allocation"] = "10%"
    else:  # aggressive
        profile["recommendations"]["equity_allocation"] = "70-80%"
        profile["recommendations"]["bond_allocation"] = "15-25%"
        profile["recommendations"]["cash_allocation"] = "5-10%"

    # Add timeframe-specific recommendations
    if profile["timeframe"] == "short-term":
        profile["recommendations"]["holding_period"] = "3-12 months"
        profile["recommendations"]["focus"] = "Technical analysis, short-term catalysts"
    elif profile["timeframe"] == "medium-term":
        profile["recommendations"]["holding_period"] = "1-3 years"
        profile["recommendations"]["focus"] = "Balanced technical and fundamental analysis"
    else:  # long-term
        profile["recommendations"]["holding_period"] = "3+ years"
        profile["recommendations"]["focus"] = "Fundamental analysis, company quality"

    return {
        "status": "success",
        "profile": profile
    }


async def calculate_portfolio_allocation(
    stocks: List[Dict[str, Any]],
    capital: float,
    risk_tolerance: str = "moderate"
) -> Dict[str, Any]:
    """
    Calculate portfolio allocation based on stock analysis and risk tolerance

    Args:
        stocks: List of stock analysis results with scores/ratings
        capital: Total capital to invest
        risk_tolerance: User's risk tolerance level

    Returns:
        Dict containing portfolio allocation recommendations
    """
    if not stocks:
        return {
            "success": False,
            "error": "No stocks provided for allocation"
        }

    # Normalize scores and calculate weights
    total_score = sum(stock.get("score", 50) for stock in stocks)

    if total_score == 0:
        # Equal weight if no scores
        equal_weight = 1.0 / len(stocks)
        weights = {stock["symbol"]: equal_weight for stock in stocks}
    else:
        weights = {
            stock["symbol"]: stock.get("score", 50) / total_score
            for stock in stocks
        }

    # Adjust weights based on risk tolerance
    if risk_tolerance == "conservative":
        # Cap individual position size at 15%
        max_weight = 0.15
        for symbol in weights:
            if weights[symbol] > max_weight:
                excess = weights[symbol] - max_weight
                weights[symbol] = max_weight
                # Distribute excess to other stocks
                other_symbols = [s for s in weights.keys() if s != symbol]
                if other_symbols:
                    per_stock_addition = excess / len(other_symbols)
                    for other_symbol in other_symbols:
                        weights[other_symbol] += per_stock_addition

    elif risk_tolerance == "aggressive":
        # Allow higher concentration in top stocks
        max_weight = 0.30
        # No adjustment needed, allow natural distribution
        pass

    else:  # moderate
        # Cap individual position size at 20%
        max_weight = 0.20
        for symbol in weights:
            if weights[symbol] > max_weight:
                excess = weights[symbol] - max_weight
                weights[symbol] = max_weight
                other_symbols = [s for s in weights.keys() if s != symbol]
                if other_symbols:
                    per_stock_addition = excess / len(other_symbols)
                    for other_symbol in other_symbols:
                        weights[other_symbol] += per_stock_addition

    # Calculate allocation amounts
    allocations = {}
    for symbol, weight in weights.items():
        amount = capital * weight
        stock_info = next((s for s in stocks if s["symbol"] == symbol), {})
        current_price = stock_info.get("current_price", 0)

        if current_price > 0:
            shares = int(amount / (current_price * 1000))  # VN stocks trade in lots of 100
            shares = (shares // 100) * 100  # Round down to nearest 100
            actual_amount = shares * current_price * 1000
        else:
            shares = 0
            actual_amount = 0

        allocations[symbol] = {
            "weight": round(weight * 100, 2),  # percentage
            "target_amount": round(amount, 0),
            "shares": shares,
            "actual_amount": round(actual_amount, 0),
            "current_price": current_price
        }

    total_allocated = sum(a["actual_amount"] for a in allocations.values())
    cash_reserve = capital - total_allocated

    return {
        "success": True,
        "allocations": allocations,
        "total_capital": capital,
        "total_allocated": total_allocated,
        "cash_reserve": cash_reserve,
        "cash_reserve_percentage": round((cash_reserve / capital) * 100, 2)
    }


async def generate_entry_strategy(
    stocks: List[Dict[str, Any]],
    timeframe: str = "medium-term"
) -> Dict[str, Any]:
    """
    Generate entry strategy for stocks based on technical analysis

    Args:
        stocks: List of stocks with technical analysis data
        timeframe: Investment timeframe

    Returns:
        Dict containing entry strategies for each stock
    """
    strategies = {}

    for stock in stocks:
        symbol = stock.get("symbol", "UNKNOWN")
        current_price = stock.get("current_price", 0)

        # Default strategy
        strategy = {
            "current_price": current_price,
            "entry_method": "Phân bổ đều",
            "positions": []
        }

        # Get technical indicators if available
        rsi = stock.get("rsi", 50)
        macd = stock.get("macd", 0)
        support = stock.get("support", current_price * 0.95)
        resistance = stock.get("resistance", current_price * 1.05)

        if timeframe == "short-term":
            # Aggressive entry for short-term
            strategy["entry_method"] = "Một lần toàn bộ"
            strategy["positions"] = [
                {
                    "percentage": 100,
                    "price_target": current_price,
                    "condition": "Mua ngay tại giá thị trường"
                }
            ]

        elif timeframe == "medium-term":
            # Split entry for medium-term
            strategy["entry_method"] = "Phân chia 2-3 đợt"

            if rsi < 40:  # Oversold
                strategy["positions"] = [
                    {
                        "percentage": 50,
                        "price_target": current_price,
                        "condition": "Mua 50% tại giá hiện tại (RSI oversold)"
                    },
                    {
                        "percentage": 50,
                        "price_target": round(current_price * 0.98, 2),
                        "condition": "Mua 50% còn lại nếu giá điều chỉnh 2%"
                    }
                ]
            elif rsi > 60:  # Overbought
                strategy["positions"] = [
                    {
                        "percentage": 30,
                        "price_target": round(current_price * 0.97, 2),
                        "condition": "Mua 30% nếu giá điều chỉnh về gần hỗ trợ"
                    },
                    {
                        "percentage": 40,
                        "price_target": round(current_price * 0.95, 2),
                        "condition": "Mua 40% nếu giá điều chỉnh sâu hơn"
                    },
                    {
                        "percentage": 30,
                        "price_target": round(support, 2),
                        "condition": "Mua 30% còn lại tại vùng hỗ trợ"
                    }
                ]
            else:  # Normal
                strategy["positions"] = [
                    {
                        "percentage": 50,
                        "price_target": current_price,
                        "condition": "Mua 50% tại giá hiện tại"
                    },
                    {
                        "percentage": 50,
                        "price_target": round(current_price * 0.97, 2),
                        "condition": "Mua 50% còn lại nếu giá điều chỉnh"
                    }
                ]

        else:  # long-term
            # Dollar cost averaging for long-term
            strategy["entry_method"] = "Mua định kỳ (DCA)"
            strategy["positions"] = [
                {
                    "percentage": 25,
                    "price_target": current_price,
                    "condition": "Mua 25% ngay"
                },
                {
                    "percentage": 25,
                    "price_target": "Theo kế hoạch",
                    "condition": "Mua 25% sau 1 tháng"
                },
                {
                    "percentage": 25,
                    "price_target": "Theo kế hoạch",
                    "condition": "Mua 25% sau 2 tháng"
                },
                {
                    "percentage": 25,
                    "price_target": "Theo kế hoạch",
                    "condition": "Mua 25% sau 3 tháng"
                }
            ]

        strategies[symbol] = strategy

    return {
        "success": True,
        "strategies": strategies,
        "timeframe": timeframe
    }


async def generate_risk_management_plan(
    stocks: List[Dict[str, Any]],
    risk_tolerance: str = "moderate",
    market_outlook: str = "neutral",
    industry_outlook: str = "neutral"
) -> Dict[str, Any]:
    """
    Generate risk management plan for portfolio

    Args:
        stocks: List of stocks in portfolio
        risk_tolerance: User's risk tolerance
        market_outlook: Overall market outlook (bullish/neutral/bearish)
        industry_outlook: Industry outlook

    Returns:
        Dict containing risk management recommendations
    """
    # Define stop-loss levels based on risk tolerance
    if risk_tolerance == "conservative":
        stop_loss_pct = 5
        take_profit_pct = 10
    elif risk_tolerance == "moderate":
        stop_loss_pct = 8
        take_profit_pct = 15
    else:  # aggressive
        stop_loss_pct = 12
        take_profit_pct = 20

    # Adjust based on market outlook
    if market_outlook == "bearish":
        stop_loss_pct = max(3, stop_loss_pct - 2)
        take_profit_pct = max(8, take_profit_pct - 5)
    elif market_outlook == "bullish":
        stop_loss_pct = min(15, stop_loss_pct + 2)
        take_profit_pct = min(30, take_profit_pct + 5)

    risk_plans = {}

    for stock in stocks:
        symbol = stock.get("symbol", "UNKNOWN")
        current_price = stock.get("current_price", 0)

        risk_plans[symbol] = {
            "stop_loss": {
                "price": round(current_price * (1 - stop_loss_pct / 100), 2),
                "percentage": -stop_loss_pct,
                "type": "Trailing stop" if risk_tolerance == "aggressive" else "Fixed stop"
            },
            "take_profit": {
                "price": round(current_price * (1 + take_profit_pct / 100), 2),
                "percentage": take_profit_pct,
                "type": "Partial profit taking"
            },
            "position_size_limit": {
                "conservative": "10-15%",
                "moderate": "15-20%",
                "aggressive": "20-30%"
            }.get(risk_tolerance, "15-20%")
        }

    return {
        "success": True,
        "risk_plans": risk_plans,
        "general_recommendations": {
            "portfolio_review_frequency": {
                "short-term": "Hàng ngày",
                "medium-term": "Hàng tuần",
                "long-term": "Hàng tháng"
            },
            "rebalancing_trigger": "Khi allocation lệch > 5% so với target",
            "market_conditions": {
                "bullish": "Có thể tăng tỷ trọng cổ phiếu",
                "neutral": "Duy trì allocation hiện tại",
                "bearish": "Giảm tỷ trọng cổ phiếu, tăng tiền mặt"
            }.get(market_outlook, "Duy trì allocation hiện tại"),
            "diversification": "Đa dạng hóa qua ít nhất 3-5 cổ phiếu khác ngành"
        }
    }


async def generate_monitoring_plan(
    stocks: List[Dict[str, Any]],
    timeframe: str = "medium-term"
) -> Dict[str, Any]:
    """
    Generate monitoring plan with key metrics to watch

    Args:
        stocks: List of stocks in portfolio
        timeframe: Investment timeframe

    Returns:
        Dict containing monitoring recommendations
    """
    monitoring_plan = {
        "success": True,
        "frequency": {
            "short-term": "Hàng ngày",
            "medium-term": "2-3 lần/tuần",
            "long-term": "Hàng tuần"
        }.get(timeframe, "Hàng tuần"),
        "key_metrics": {}
    }

    # Define key metrics based on timeframe
    if timeframe == "short-term":
        general_metrics = [
            "Giá và khối lượng giao dịch",
            "RSI, MACD, Bollinger Bands",
            "Tin tức và sự kiện trong ngày",
            "Thanh khoản thị trường"
        ]
    elif timeframe == "medium-term":
        general_metrics = [
            "Xu hướng giá tuần/tháng",
            "Các chỉ số kỹ thuật chính",
            "Kết quả kinh doanh quý",
            "Tin tức ngành và công ty",
            "So sánh với peers"
        ]
    else:  # long-term
        general_metrics = [
            "Kết quả kinh doanh năm",
            "ROE, ROA, profit margins",
            "Tăng trưởng doanh thu/lợi nhuận",
            "Tình hình nợ và dòng tiền",
            "Chiến lược và định hướng công ty",
            "Thay đổi ban lãnh đạo"
        ]

    monitoring_plan["general_metrics"] = general_metrics

    # Stock-specific monitoring
    for stock in stocks:
        symbol = stock.get("symbol", "UNKNOWN")
        monitoring_plan["key_metrics"][symbol] = {
            "price_alerts": [
                f"Giá chạm mức hỗ trợ",
                f"Giá chạm mức kháng cự",
                f"Giá vượt {stock.get('ma20', 'MA20')}"
            ],
            "volume_alerts": [
                "Khối lượng tăng đột biến (> 2x TB)",
                "Khối lượng giảm mạnh"
            ],
            "fundamental_events": [
                "Công bố KQKD quý/năm",
                "Họp ĐHCĐ",
                "Thay đổi lãnh đạo",
                "Tin M&A hoặc dự án lớn"
            ]
        }

    return monitoring_plan


async def generate_dca_plan(
    symbol: str,
    monthly_investment: float,
    duration_months: int = 12,
    current_price: float = None,
    price_trend: str = "neutral",
    start_month: str = None
) -> Dict[str, Any]:
    """
    Generate detailed DCA (Dollar Cost Averaging) plan with monthly breakdown

    Args:
        symbol: Stock symbol (e.g., VCB, FPT)
        monthly_investment: Monthly investment amount in VND
        duration_months: Number of months for DCA plan
        current_price: Current stock price (in VND, e.g., 97400 for 97.4k)
        price_trend: Expected price trend (bullish/neutral/bearish)
        start_month: Starting month (e.g., "01/2025"), defaults to current

    Returns:
        Dict containing detailed DCA plan with monthly breakdown
    """
    from datetime import datetime, timedelta

    # Default start month
    if not start_month:
        now = datetime.now()
        start_month = f"{now.month:02d}/{now.year}"

    # Parse start month
    try:
        start_date = datetime.strptime(f"01/{start_month}", "%d/%m/%Y")
    except:
        start_date = datetime.now().replace(day=1)

    # Get current price if not provided
    if not current_price or current_price == 0:
        # Try to fetch from database
        try:
            from ..shared.database import execute_sql_in_thread
            query = f"""
                SELECT close * 1000 as price FROM stock.stock_prices_1d
                WHERE ticker = '{symbol.upper()}'
                ORDER BY time DESC LIMIT 1;
            """
            records, is_error = execute_sql_in_thread(query)
            if not is_error and records and 'price' in records[0]:
                current_price = float(records[0]['price'])
            else:
                current_price = 100000  # Default fallback
        except:
            current_price = 100000

    # Price adjustment factors based on trend
    trend_factors = {
        "bullish": {"monthly_change": 0.015, "volatility": 0.03},    # +1.5%/month avg
        "neutral": {"monthly_change": 0.005, "volatility": 0.02},    # +0.5%/month avg
        "bearish": {"monthly_change": -0.01, "volatility": 0.025}    # -1%/month avg
    }

    factor = trend_factors.get(price_trend, trend_factors["neutral"])

    # Generate monthly plan
    monthly_plan = []
    total_shares = 0
    total_invested = 0
    estimated_price = current_price

    for month in range(duration_months):
        month_date = start_date + timedelta(days=30 * month)
        month_str = f"{month_date.month:02d}/{month_date.year}"

        # Estimate price with some variation
        if month > 0:
            # Apply trend + some randomness simulation (use month index as seed)
            import math
            variation = math.sin(month * 0.5) * factor["volatility"]
            estimated_price = estimated_price * (1 + factor["monthly_change"] + variation)

        # Calculate shares (VN stocks trade in lots of 100)
        # Fix: Correct calculation - first get integer shares, then round to lot of 100
        shares_exact = monthly_investment / estimated_price
        shares_int = int(shares_exact)  # First convert to integer
        shares_rounded = (shares_int // 100) * 100  # Then round DOWN to nearest 100 (lot)

        if shares_rounded == 0:
            shares_rounded = 100  # Minimum 1 lot

        # IMPORTANT: For DCA, actual_investment = monthly_investment (fixed amount per month)
        # The shares calculated above are based on this fixed investment
        # User invests the SAME amount each month, shares vary based on price
        actual_investment = monthly_investment

        monthly_plan.append({
            "month": month + 1,
            "date": month_str,
            "estimated_price": round(estimated_price, 0),
            "target_investment": monthly_investment,
            "shares_to_buy": shares_rounded,
            "actual_investment": round(actual_investment, 0),
            "cumulative_shares": total_shares + shares_rounded,
            "cumulative_invested": round(total_invested + actual_investment, 0)
        })

        total_shares += shares_rounded
        total_invested += actual_investment

    # Calculate summary statistics
    # For DCA, average price = weighted average of purchase prices
    # Sum(shares_bought * price_at_purchase) / total_shares
    total_cost_by_price = sum(
        entry["shares_to_buy"] * entry["estimated_price"]
        for entry in monthly_plan
    )
    avg_price = total_cost_by_price / total_shares if total_shares > 0 else 0
    final_price = monthly_plan[-1]["estimated_price"] if monthly_plan else current_price
    final_value = total_shares * final_price
    profit_loss = final_value - total_invested
    profit_loss_pct = (profit_loss / total_invested * 100) if total_invested > 0 else 0

    # Generate recommendations
    recommendations = []
    if price_trend == "bullish":
        recommendations.append("Xu hướng tăng: Cân nhắc tăng số tiền đầu tư mỗi tháng")
        recommendations.append("Mua sớm trong tháng để tận dụng giá thấp hơn")
    elif price_trend == "bearish":
        recommendations.append("Xu hướng giảm: DCA là chiến lược phù hợp để giảm giá vốn trung bình")
        recommendations.append("Cân nhắc tăng mua khi giá giảm mạnh")
    else:
        recommendations.append("Duy trì kỷ luật đầu tư đều đặn hàng tháng")

    recommendations.extend([
        "Đặt lệnh mua định kỳ vào ngày cố định mỗi tháng",
        "Theo dõi RSI - mua thêm khi RSI < 30 (oversold)",
        "Không thay đổi kế hoạch khi thị trường biến động ngắn hạn",
        f"Mục tiêu: Tích lũy {total_shares:,} cổ phiếu {symbol} sau {duration_months} tháng"
    ])

    return {
        "status": "success",
        "symbol": symbol.upper(),
        "plan_summary": {
            "strategy": "Dollar Cost Averaging (DCA)",
            "monthly_investment": monthly_investment,
            "duration_months": duration_months,
            "start_month": start_month,
            "current_price": current_price,
            "price_trend": price_trend
        },
        "monthly_breakdown": monthly_plan,
        "projections": {
            "total_investment": round(total_invested, 0),
            "total_shares": total_shares,
            "average_price": round(avg_price, 0),
            "final_estimated_price": round(final_price, 0),
            "final_portfolio_value": round(final_value, 0),
            "estimated_profit_loss": round(profit_loss, 0),
            "estimated_return_pct": round(profit_loss_pct, 2)
        },
        "recommendations": recommendations,
        "disclaimer": "Đây là kế hoạch dự kiến dựa trên giả định. Giá thực tế có thể khác biệt đáng kể."
    }


# Export all tools
__all__ = [
    'gather_investment_profile',
    'calculate_portfolio_allocation',
    'generate_entry_strategy',
    'generate_risk_management_plan',
    'generate_monitoring_plan',
    'generate_dca_plan'
]
