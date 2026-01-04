"""
Alert Manager Agent

Specialized in managing stock price alerts.

Based on OLD system's alert_agent pattern.
"""

import os
import sys
from typing import Dict, Optional, AsyncIterator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))


class AlertManager:
    """
    Specialist for alert management

    Tools (3):
    - create_alert: Create new price/indicator alert
    - get_user_alerts: Get user's alerts
    - delete_alert: Delete alert

    Simple, focused agent - no complex reasoning needed.
    """

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client

        self.stats = {
            "alerts_created": 0,
            "alerts_deleted": 0,
            "alerts_viewed": 0
        }

    async def create_alert(
        self,
        user_id: str,
        symbol: str,
        alert_type: str,
        condition: str,
        target_value: Optional[float] = None
    ) -> str:
        """Create a new alert"""
        self.stats["alerts_created"] += 1

        result = await self.mcp_client.call_tool(
            "create_alert",
            {
                "user_id": user_id,
                "symbol": symbol,
                "alert_type": alert_type,
                "condition": condition,
                "target_value": target_value
            }
        )

        if result.get("status") == "success":
            return f"✅ {result.get('message')}"
        else:
            return f"❌ {result.get('message')}"

    async def get_alerts(self, user_id: str) -> str:
        """Get user's alerts"""
        self.stats["alerts_viewed"] += 1

        result = await self.mcp_client.call_tool(
            "get_user_alerts",
            {"user_id": user_id}
        )

        if result.get("status") != "success":
            return f"❌ {result.get('message')}"

        alerts = result.get("alerts", [])
        if not alerts:
            return "📭 Bạn chưa có cảnh báo nào."

        # Format output
        output = [f"🔔 **Cảnh báo của bạn** ({len(alerts)}):\n"]

        for alert in alerts:
            output.append(
                f"• **{alert['symbol']}** - {alert.get('type', 'N/A')}\n"
                f"  Điều kiện: {alert.get('condition', 'N/A')}\n"
                f"  ID: {alert['id']}\n"
            )

        return "\n".join(output)

    async def delete_alert(self, user_id: str, alert_id: int) -> str:
        """Delete an alert"""
        self.stats["alerts_deleted"] += 1

        result = await self.mcp_client.call_tool(
            "delete_alert",
            {
                "user_id": user_id,
                "alert_id": alert_id
            }
        )

        if result.get("status") == "success":
            return f"✅ {result.get('message')}"
        else:
            return f"❌ {result.get('message')}"

    def get_stats(self) -> Dict:
        return self.stats.copy()
