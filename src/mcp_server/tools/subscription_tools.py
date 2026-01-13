"""
Subscription management tools for MCP server
"""
import asyncio
import logging
from ..shared.database import execute_sql_in_thread
from ..shared.constants import validate_symbol, VN30_STOCKS

logger = logging.getLogger(__name__)


async def create_subscription_mcp(user_id: str, symbol: str) -> dict:
    """
    Create a new subscription for a user

    Args:
        user_id: User ID
        symbol: Stock symbol to subscribe to (must be in VN30)

    Returns:
        dict: Result of subscription creation with validation
    """
    # Validate symbol before proceeding
    is_valid_symbol, symbol_error = validate_symbol(symbol)
    if not is_valid_symbol:
        logger.warning(f"Invalid symbol for subscription: {symbol}")
        return {
            "status": "error",
            "message": symbol_error,
            "validation_error": "invalid_symbol"
        }

    # Get full stock name for better messaging
    stock_name = VN30_STOCKS.get(symbol.upper(), symbol)

    def _sync_create():
        try:
            # Check if subscription already exists
            check_query = f"""
            SELECT id FROM subscriptions
            WHERE user_id = '{user_id}' AND symbol = '{symbol}' AND is_active = true;
            """

            existing, is_error = execute_sql_in_thread(check_query)

            if not is_error and existing and 'message' not in existing[0]:
                return {
                    "status": "info",
                    "message": f"Bạn đã theo dõi {symbol} ({stock_name}) rồi"
                }

            # Create new subscription
            sql_query = f"""
            INSERT INTO subscriptions (user_id, symbol, is_active)
            VALUES ('{user_id}', '{symbol}', true)
            RETURNING id, user_id, symbol, created_at;
            """

            records, is_error = execute_sql_in_thread(sql_query)

            if is_error:
                raise Exception(records[0].get("error", "Failed to create subscription"))

            if records and len(records) > 0:
                subscription = records[0]
                return {
                    "status": "success",
                    "message": f"Đã theo dõi {symbol} ({stock_name}) thành công",
                    "subscription": dict(subscription),
                    "stock_name": stock_name
                }
            else:
                raise Exception("No subscription data returned after creation")

        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return {"status": "error", "message": str(e)}

    return await asyncio.to_thread(_sync_create)


async def get_user_subscriptions_mcp(user_id: str) -> dict:
    """
    Get all subscriptions for a user

    Args:
        user_id: User ID

    Returns:
        dict: List of user's subscriptions
    """
    def _sync_get():
        try:
            sql_query = f"""
            SELECT id, user_id, symbol, is_active, created_at
            FROM subscriptions
            WHERE user_id = '{user_id}' AND is_active = true
            ORDER BY created_at DESC;
            """

            records, is_error = execute_sql_in_thread(sql_query)

            if is_error:
                raise Exception(records[0].get("error", "Failed to fetch subscriptions"))

            subscriptions = [dict(record) for record in records if 'message' not in record]

            return {
                "status": "success",
                "count": len(subscriptions),
                "subscriptions": subscriptions
            }

        except Exception as e:
            logger.error(f"Error fetching subscriptions: {e}")
            return {"status": "error", "message": str(e)}

    return await asyncio.to_thread(_sync_get)


async def delete_subscription_mcp(user_id: str, subscription_id: int) -> dict:
    """
    Delete a subscription

    Args:
        user_id: User ID
        subscription_id: Subscription ID to delete

    Returns:
        dict: Result of deletion
    """
    def _sync_delete():
        try:
            sql_query = f"""
            UPDATE subscriptions
            SET is_active = false
            WHERE id = {subscription_id} AND user_id = '{user_id}'
            RETURNING id, symbol;
            """

            records, is_error = execute_sql_in_thread(sql_query)

            if is_error:
                raise Exception(records[0].get("error", "Failed to delete subscription"))

            if records and len(records) > 0:
                deleted_sub = records[0]
                return {
                    "status": "success",
                    "message": f"Subscription {subscription_id} for {deleted_sub.get('symbol')} deleted successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Subscription {subscription_id} not found or already deleted"
                }

        except Exception as e:
            logger.error(f"Error deleting subscription: {e}")
            return {"status": "error", "message": str(e)}

    return await asyncio.to_thread(_sync_delete)
