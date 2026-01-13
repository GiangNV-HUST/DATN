"""
Alert management tools for MCP server
"""
import asyncio
import logging
from typing import Optional
from ..shared.database import execute_sql_in_thread
from ..shared.constants import (
    validate_symbol,
    validate_alert_type,
    validate_alert_condition,
    get_alert_description
)

logger = logging.getLogger(__name__)


async def create_alert_mcp(
    user_id: str,
    symbol: str,
    alert_type: str,
    target_value: float,
    condition: str
) -> dict:
    """
    Create a new alert for a user

    Args:
        user_id: User ID
        symbol: Stock symbol (must be in VN30)
        alert_type: Type of alert (e.g., 'price', 'ma5', 'ma10', 'rsi', 'macd')
        target_value: Target value for alert
        condition: Condition (e.g., 'above', 'below', 'cross_above', 'cross_below')

    Returns:
        dict: Result of alert creation with validation
    """
    # Validate symbol
    is_valid_symbol, symbol_error = validate_symbol(symbol)
    if not is_valid_symbol:
        logger.warning(f"Invalid symbol: {symbol}")
        return {
            "status": "error",
            "message": symbol_error,
            "validation_error": "invalid_symbol"
        }

    # Validate alert type
    is_valid_type, type_error = validate_alert_type(alert_type)
    if not is_valid_type:
        logger.warning(f"Invalid alert type: {alert_type}")
        return {
            "status": "error",
            "message": type_error,
            "validation_error": "invalid_alert_type"
        }

    # Validate condition for alert type
    is_valid_condition, condition_error = validate_alert_condition(alert_type, condition)
    if not is_valid_condition:
        logger.warning(f"Invalid condition '{condition}' for alert type '{alert_type}'")
        return {
            "status": "error",
            "message": condition_error,
            "validation_error": "invalid_condition"
        }

    # Get human-readable description
    alert_description = get_alert_description(alert_type, condition, target_value)

    def _sync_create():
        try:
            sql_query = f"""
            INSERT INTO alerts (user_id, symbol, alert_type, target_value, condition, is_active)
            VALUES ('{user_id}', '{symbol}', '{alert_type}', {target_value}, '{condition}', true)
            RETURNING id, user_id, symbol, alert_type, target_value, condition, created_at;
            """

            records, is_error = execute_sql_in_thread(sql_query)

            if is_error:
                raise Exception(records[0].get("error", "Failed to create alert"))

            if records and len(records) > 0:
                alert = records[0]
                return {
                    "status": "success",
                    "message": f"Cảnh báo đã được tạo cho {symbol}: {alert_description}",
                    "alert": dict(alert),
                    "description": alert_description
                }
            else:
                raise Exception("No alert data returned after creation")

        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return {"status": "error", "message": str(e)}

    return await asyncio.to_thread(_sync_create)


async def get_user_alerts_mcp(user_id: str) -> dict:
    """
    Get all alerts for a user

    Args:
        user_id: User ID

    Returns:
        dict: List of user's alerts
    """
    def _sync_get():
        try:
            sql_query = f"""
            SELECT id, user_id, symbol, alert_type, target_value, condition, is_active, created_at, triggered_at
            FROM alerts
            WHERE user_id = '{user_id}' AND is_active = true
            ORDER BY created_at DESC;
            """

            records, is_error = execute_sql_in_thread(sql_query)

            if is_error:
                raise Exception(records[0].get("error", "Failed to fetch alerts"))

            alerts = [dict(record) for record in records if 'message' not in record]

            return {
                "status": "success",
                "count": len(alerts),
                "alerts": alerts
            }

        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return {"status": "error", "message": str(e)}

    return await asyncio.to_thread(_sync_get)


async def delete_alert_mcp(user_id: str, alert_id: int) -> dict:
    """
    Delete an alert

    Args:
        user_id: User ID
        alert_id: Alert ID to delete

    Returns:
        dict: Result of deletion
    """
    def _sync_delete():
        try:
            sql_query = f"""
            UPDATE alerts
            SET is_active = false
            WHERE id = {alert_id} AND user_id = '{user_id}'
            RETURNING id, symbol;
            """

            records, is_error = execute_sql_in_thread(sql_query)

            if is_error:
                raise Exception(records[0].get("error", "Failed to delete alert"))

            if records and len(records) > 0:
                deleted_alert = records[0]
                return {
                    "status": "success",
                    "message": f"Alert {alert_id} for {deleted_alert.get('symbol')} deleted successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Alert {alert_id} not found or already deleted"
                }

        except Exception as e:
            logger.error(f"Error deleting alert: {e}")
            return {"status": "error", "message": str(e)}

    return await asyncio.to_thread(_sync_delete)
