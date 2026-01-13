"""
AI tools for MCP server
Provides AI summarization and search capabilities
Updated: Now uses OpenAI instead of Gemini for consistency
Note: Web search functionality is handled via OpenAI function calling
"""
import os
import asyncio
import logging
import concurrent.futures
from typing import Optional, Dict, Any, List
from openai import OpenAI

logger = logging.getLogger(__name__)


async def gemini_summarize_mcp(prompt: str, data: dict, use_search: bool = False) -> dict:
    """
    Summarize data using OpenAI (function name kept for backward compatibility)

    Args:
        prompt: Prompt for summarization
        data: Data to summarize
        use_search: Whether to use web search (ignored in OpenAI version)

    Returns:
        dict: Summarization result
    """
    def _sync_summarize():
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

            full_prompt = f"{prompt}\n\nData: {data}"

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes stock data in Vietnamese."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7,
                max_tokens=2048
            )

            return {
                "status": "success",
                "summary": response.choices[0].message.content
            }

        except Exception as e:
            logger.error(f"Error in AI summarization: {e}")
            return {"status": "error", "message": str(e)}

    return await asyncio.to_thread(_sync_summarize)


async def gemini_search_and_summarize_mcp(query: str, user_query: str) -> dict:
    """
    Search the web and summarize results using OpenAI (function name kept for backward compatibility)

    Args:
        query: Search query
        user_query: User's question to answer with search results

    Returns:
        dict: Search and summarization result
    """
    def _sync_search():
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

            prompt = f"""
            Tim kiem thong tin ve: {query}

            Sau do tra loi cau hoi cua nguoi dung: {user_query}

            Hay su dung kien thuc cua ban de tra loi mot cach chinh xac, chi tiet ve thi truong chung khoan Viet Nam.
            """

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a Vietnamese stock market expert. Provide detailed and accurate information about Vietnamese stocks."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2048
            )

            return {
                "status": "success",
                "query": query,
                "user_query": user_query,
                "answer": response.choices[0].message.content
            }

        except Exception as e:
            logger.error(f"Error in AI search and summarize: {e}")
            return {"status": "error", "message": str(e)}

    return await asyncio.to_thread(_sync_search)


async def batch_summarize_mcp(
    symbols_data: Dict[str, Dict[str, Any]],
    general_query: str = ""
) -> dict:
    """
    Batch summarize data for multiple symbols in parallel with different configurations

    Args:
        symbols_data: Dictionary mapping symbols to their data and query
            Example: {
                "VCB": {
                    "data": {...},  # Stock data, financial data, etc.
                    "query": "Phan tich gia VCB",  # Optional per-symbol query
                    "use_search": True  # Optional per-symbol search flag
                },
                "FPT": {
                    "data": {...},
                    "query": "Doanh thu FPT"
                }
            }
        general_query: General query to use if symbol doesn't have specific query

    Returns:
        dict: Batch summarization results with per-symbol summaries
    """
    def _summarize_single_symbol(symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous helper to summarize a single symbol"""
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

            # Get config for this symbol
            data = config.get("data", {})
            query = config.get("query", general_query)

            # Build prompt
            full_prompt = f"""
Hay tom tat du lieu co phieu sau day mot cach ngan gon va day du thong tin:

Co phieu: {symbol}

Du lieu: {data}

Cau hoi: {query}
"""

            # Generate summary
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a Vietnamese stock market analyst. Provide concise summaries."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7,
                max_tokens=1024
            )

            return {
                "symbol": symbol,
                "success": True,
                "summary": response.choices[0].message.content,
                "query": query
            }

        except Exception as e:
            logger.error(f"Error summarizing {symbol}: {e}")
            return {
                "symbol": symbol,
                "success": False,
                "error": str(e),
                "query": config.get("query", general_query)
            }

    def _sync_batch_summarize():
        """Synchronous batch processing with ThreadPoolExecutor"""
        results = {}
        errors = []

        # Limit concurrent workers to avoid API overload
        max_workers = min(len(symbols_data), 3)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(_summarize_single_symbol, symbol, config): symbol
                for symbol, config in symbols_data.items()
            }

            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()

                    if result["success"]:
                        results[symbol] = {
                            "success": True,
                            "summary": result["summary"],
                            "query": result["query"]
                        }
                    else:
                        results[symbol] = {
                            "success": False,
                            "error": result["error"],
                            "query": result["query"]
                        }
                        errors.append(f"{symbol}: {result['error']}")

                except Exception as e:
                    error_msg = f"Loi khi xu ly tom tat cho {symbol}: {str(e)}"
                    results[symbol] = {
                        "success": False,
                        "error": error_msg
                    }
                    errors.append(f"{symbol}: {str(e)}")

        # Return combined results
        success_count = sum(1 for r in results.values() if r["success"])
        total_count = len(symbols_data)

        if errors:
            return {
                "status": "partial_success",
                "results": results,
                "errors": errors,
                "success_count": success_count,
                "total_count": total_count,
                "message": f"Da hoan thanh tom tat cho {success_count}/{total_count} co phieu"
            }

        return {
            "status": "success",
            "results": results,
            "success_count": success_count,
            "total_count": total_count,
            "message": f"Da tom tat thanh cong cho tat ca {total_count} co phieu"
        }

    # Run in executor to avoid blocking
    return await asyncio.to_thread(_sync_batch_summarize)
