"""
Stock Discovery Tools for MCP Server
Helps discover potential stocks based on criteria and web search
"""

import asyncio
import re
from typing import Dict, Any, List, Optional
import json


async def search_potential_stocks(
    query: str,
    investment_goal: str = "growth",
    risk_tolerance: str = "moderate",
    timeframe: str = "medium-term",
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Search for potential stocks using web search
    This is a placeholder that should be integrated with actual search functionality

    Args:
        query: Search query for finding stocks
        investment_goal: User's investment goal
        risk_tolerance: User's risk tolerance
        timeframe: Investment timeframe
        max_results: Maximum number of stocks to return

    Returns:
        Dict containing search results with stock symbols and reasons
    """
    # This is a simplified version. In production, this would call:
    # - Google Search API or web scraping
    # - Financial news APIs
    # - Stock screener APIs

    return {
        "status": "success",
        "query": query,
        "stocks": [],  # Placeholder for discovered stocks
        "search_results": {
            "search_summary": f"Tìm kiếm cổ phiếu tiềm năng cho mục tiêu '{investment_goal}' "
                            f"với mức độ rủi ro '{risk_tolerance}' và khung thời gian '{timeframe}'",
            "sources": [
                "Web search results",
                "Financial news",
                "Analyst recommendations"
            ],
            "note": "Kết quả tìm kiếm cần được kết hợp với phân tích định lượng từ TCBS"
        },
        "max_results": max_results
    }


async def extract_stock_symbols(
    text: str,
    market: str = "HOSE"
) -> List[str]:
    """
    Extract stock symbols from text (search results, articles, etc.)

    Args:
        text: Text containing stock symbols
        market: Market to filter (HOSE, HNX, UPCOM)

    Returns:
        List of extracted stock symbols
    """
    # Common Vietnamese stock symbol pattern: 3-4 uppercase letters
    pattern = r'\b[A-Z]{3,4}\b'
    matches = re.findall(pattern, text)

    # Filter out common false positives
    exclude_words = {
        'VND', 'USD', 'GDP', 'CEO', 'CFO', 'IPO', 'HOSE', 'HNX', 'UPCOM',
        'ETF', 'VN30', 'HNX30', 'API', 'HTML', 'HTTP', 'HTTPS', 'WWW'
    }

    symbols = [m for m in matches if m not in exclude_words]

    # Remove duplicates while preserving order
    seen = set()
    unique_symbols = []
    for symbol in symbols:
        if symbol not in seen:
            seen.add(symbol)
            unique_symbols.append(symbol)

    return unique_symbols


async def filter_stocks_by_criteria(
    symbols: List[str],
    criteria: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Filter stocks based on investment criteria
    This integrates with TCBS data to get quantitative metrics

    Args:
        symbols: List of stock symbols to filter
        criteria: Filtering criteria (price range, market cap, PE ratio, etc.)

    Returns:
        Dict containing filtered stocks with their data
    """
    try:
        # Import get_stock_details_from_tcbs_mcp
        from .stock_tools import get_stock_details_from_tcbs_mcp
        import logging

        # Fetch TCBS data for all symbols
        tcbs_result = await get_stock_details_from_tcbs_mcp(symbols)

        if tcbs_result['status'] == 'error':
            return {
                "success": False,
                "message": f"Error fetching TCBS data: {tcbs_result['message']}",
                "filtered_stocks": []
            }

        stocks_data = tcbs_result.get('data', [])

        if not stocks_data:
            return {
                "success": False,
                "message": "No data found for provided symbols",
                "filtered_stocks": []
            }

        # Default criteria
        default_criteria = {
            "min_market_cap": 1000,  # billion VND
            "max_pe": 20,
            "min_roe": 10,  # percent
            "min_revenue_growth": 5,  # percent YoY
            "min_liquidity": 100_000  # shares/day average volume
        }

        # Merge with provided criteria
        filter_criteria = {**default_criteria, **criteria}

        # Filter stocks based on criteria
        filtered_stocks = []
        for stock in stocks_data:
            passes = True
            reasons = []

            # Check market cap
            if 'market_cap' in stock and stock['market_cap'] is not None:
                if stock['market_cap'] < filter_criteria.get('min_market_cap', 0):
                    passes = False
                    reasons.append(f"Market cap {stock['market_cap']} < {filter_criteria['min_market_cap']}")

            # Check PE ratio
            if 'pe' in stock and stock['pe'] is not None:
                max_pe = filter_criteria.get('max_pe')
                if max_pe and stock['pe'] > max_pe:
                    passes = False
                    reasons.append(f"PE {stock['pe']} > {max_pe}")

            # Check ROE
            if 'roe' in stock and stock['roe'] is not None:
                min_roe = filter_criteria.get('min_roe')
                if min_roe and stock['roe'] < min_roe:
                    passes = False
                    reasons.append(f"ROE {stock['roe']} < {min_roe}")

            # Check revenue growth
            if 'revenue_growth_1y' in stock and stock['revenue_growth_1y'] is not None:
                min_growth = filter_criteria.get('min_revenue_growth')
                if min_growth and stock['revenue_growth_1y'] < min_growth:
                    passes = False
                    reasons.append(f"Revenue growth {stock['revenue_growth_1y']} < {min_growth}")

            # Check liquidity (avg trading value)
            if 'avg_trading_value_20d' in stock and stock['avg_trading_value_20d'] is not None:
                min_liquidity = filter_criteria.get('min_liquidity')
                if min_liquidity and stock['avg_trading_value_20d'] < min_liquidity:
                    passes = False
                    reasons.append(f"Liquidity {stock['avg_trading_value_20d']} < {min_liquidity}")

            if passes:
                filtered_stocks.append(stock)
            else:
                # Log why stock was filtered out
                logging.info(f"Stock {stock.get('ticker')} filtered out: {', '.join(reasons)}")

        return {
            "success": True,
            "criteria_applied": filter_criteria,
            "symbols_checked": symbols,
            "stocks_found": len(stocks_data),
            "stocks_passed_filter": len(filtered_stocks),
            "filtered_stocks": filtered_stocks,
            "message": f"Filtered {len(filtered_stocks)}/{len(stocks_data)} stocks that meet criteria"
        }

    except Exception as e:
        import logging
        logging.error(f"Error in filter_stocks_by_criteria: {str(e)}")
        return {
            "success": False,
            "message": f"Error filtering stocks: {str(e)}",
            "filtered_stocks": []
        }


async def rank_stocks_by_score(
    stocks: List[Dict[str, Any]],
    ranking_method: str = "composite"
) -> List[Dict[str, Any]]:
    """
    Rank stocks by composite score based on multiple factors

    Args:
        stocks: List of stocks with their metrics
        ranking_method: Method to rank (composite, growth, value, momentum)

    Returns:
        List of stocks ranked by score
    """
    scored_stocks = []

    for stock in stocks:
        score = 0

        if ranking_method == "composite":
            # Balanced scoring across multiple factors
            # Growth factors (40%)
            revenue_growth = stock.get("revenue_growth_yoy", 0)
            profit_growth = stock.get("profit_growth_yoy", 0)
            score += (revenue_growth / 100) * 20  # Max 20 points
            score += (profit_growth / 100) * 20   # Max 20 points

            # Value factors (30%)
            pe_ratio = stock.get("pe", 100)
            pb_ratio = stock.get("pb", 10)
            # Lower is better for PE/PB
            if pe_ratio > 0:
                score += max(0, (30 - pe_ratio) / 3)  # Max 15 points
            if pb_ratio > 0:
                score += max(0, (10 - pb_ratio) * 1.5)  # Max 15 points

            # Profitability (20%)
            roe = stock.get("roe", 0)
            score += min(roe, 20)  # Max 20 points

            # Liquidity (10%)
            avg_volume = stock.get("avg_volume", 0)
            if avg_volume > 1_000_000:
                score += 10
            elif avg_volume > 500_000:
                score += 7
            elif avg_volume > 100_000:
                score += 5
            else:
                score += 2

        elif ranking_method == "growth":
            # Focus on growth metrics
            revenue_growth = stock.get("revenue_growth_yoy", 0)
            profit_growth = stock.get("profit_growth_yoy", 0)
            roe = stock.get("roe", 0)

            score = (revenue_growth * 0.4) + (profit_growth * 0.4) + (roe * 0.2)

        elif ranking_method == "value":
            # Focus on valuation metrics
            pe_ratio = stock.get("pe", 100)
            pb_ratio = stock.get("pb", 10)
            dividend_yield = stock.get("dividend_yield", 0)

            # Lower PE/PB is better
            pe_score = max(0, (30 - pe_ratio) / 0.3) if pe_ratio > 0 else 0
            pb_score = max(0, (5 - pb_ratio) * 10) if pb_ratio > 0 else 0

            score = (pe_score * 0.4) + (pb_score * 0.3) + (dividend_yield * 10 * 0.3)

        elif ranking_method == "momentum":
            # Focus on price momentum
            returns_1m = stock.get("returns_1m", 0)
            returns_3m = stock.get("returns_3m", 0)
            rsi = stock.get("rsi", 50)

            score = (returns_1m * 0.4) + (returns_3m * 0.3) + ((50 - abs(50 - rsi)) * 0.3)

        stock_with_score = {**stock, "composite_score": round(score, 2)}
        scored_stocks.append(stock_with_score)

    # Sort by score descending
    ranked_stocks = sorted(scored_stocks, key=lambda x: x.get("composite_score", 0), reverse=True)

    return ranked_stocks


async def discover_stocks_by_profile(
    investment_profile: Dict[str, Any],
    max_stocks: int = 5
) -> Dict[str, Any]:
    """
    Main function to discover stocks based on complete investment profile
    Combines search, filtering, and ranking

    Args:
        investment_profile: Complete user investment profile
        max_stocks: Maximum number of stocks to recommend

    Returns:
        Dict containing discovered stocks with reasons
    """
    goals = investment_profile.get("goals", "growth")
    risk_tolerance = investment_profile.get("risk_tolerance", "moderate")
    timeframe = investment_profile.get("timeframe", "medium-term")

    # Build search query based on profile
    if goals == "growth":
        search_terms = "cổ phiếu tăng trưởng cao tiềm năng"
        ranking_method = "growth"
    elif goals == "income":
        search_terms = "cổ phiếu cổ tức cao ổn định"
        ranking_method = "value"
    elif goals == "preservation":
        search_terms = "cổ phiếu blue chip an toàn"
        ranking_method = "value"
    else:  # balanced
        search_terms = "cổ phiếu đầu tư cân bằng"
        ranking_method = "composite"

    # Add timeframe context
    if timeframe == "short-term":
        search_terms += " ngắn hạn"
    elif timeframe == "long-term":
        search_terms += " dài hạn"

    # Define filtering criteria based on risk tolerance
    if risk_tolerance == "conservative":
        criteria = {
            "min_market_cap": 10000,  # Large cap only
            "max_pe": 15,
            "min_roe": 12,
            "min_dividend_yield": 3
        }
    elif risk_tolerance == "aggressive":
        criteria = {
            "min_market_cap": 500,  # Include small caps
            "max_pe": 30,
            "min_roe": 8,
            "min_revenue_growth": 15
        }
    else:  # moderate
        criteria = {
            "min_market_cap": 3000,  # Mid-large cap
            "max_pe": 20,
            "min_roe": 10,
            "min_revenue_growth": 8
        }

    # Execute discovery workflow
    # 1. Search for stocks (placeholder - needs actual implementation)
    search_results = await search_potential_stocks(
        query=search_terms,
        investment_goal=goals,
        risk_tolerance=risk_tolerance,
        timeframe=timeframe,
        max_results=max_stocks * 2  # Get more to filter down
    )

    # 2. Return structured discovery result
    return {
        "success": True,
        "investment_profile": investment_profile,
        "search_query": search_terms,
        "ranking_method": ranking_method,
        "criteria": criteria,
        "max_stocks": max_stocks,
        "discovery_workflow": [
            "1. Tìm kiếm cổ phiếu dựa trên profile",
            "2. Trích xuất mã chứng khoán từ kết quả tìm kiếm",
            "3. Lọc theo tiêu chí định lượng (TCBS data)",
            "4. Xếp hạng theo composite score",
            "5. Trả về top stocks phù hợp nhất"
        ],
        "note": "Workflow này cần được tích hợp với: Google Search API, TCBS API, và Stock Screener tools"
    }


async def combine_search_and_quantitative_data(
    search_results: Dict[str, Any],
    quantitative_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Combine qualitative search results with quantitative stock data

    Args:
        search_results: Results from web search about stocks
        quantitative_data: Quantitative metrics from TCBS or other sources

    Returns:
        Dict combining both sources with comprehensive stock recommendations
    """
    combined_stocks = []

    # Extract symbols from search results
    search_text = str(search_results)
    symbols = await extract_stock_symbols(search_text)

    for symbol in symbols:
        stock_data = quantitative_data.get(symbol, {})

        combined_stocks.append({
            "symbol": symbol,
            "qualitative_reasons": f"Được đề cập trong search results về {search_results.get('query', '')}",
            "quantitative_data": stock_data,
            "combined_score": stock_data.get("composite_score", 0)
        })

    # Sort by combined score
    combined_stocks.sort(key=lambda x: x.get("combined_score", 0), reverse=True)

    return {
        "success": True,
        "combined_stocks": combined_stocks,
        "sources": {
            "qualitative": "Web search, news, analyst reports",
            "quantitative": "TCBS financial data, technical indicators"
        }
    }


# Export all tools
__all__ = [
    'search_potential_stocks',
    'extract_stock_symbols',
    'filter_stocks_by_criteria',
    'rank_stocks_by_score',
    'discover_stocks_by_profile',
    'combine_search_and_quantitative_data'
]
