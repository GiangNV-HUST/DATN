"""
Subscription Manager Agent

Specialized in managing user subscriptions for premium features.

Based on OLD system's subscription_agent pattern.
"""

import os
import sys
from typing import Dict, Optional, AsyncIterator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ai_agent_mcp'))


class SubscriptionManager:
    """
    Specialist for subscription management

    Tools (3):
    - create_subscription: Create new subscription
    - get_user_subscriptions: Get user's subscriptions
    - delete_subscription: Cancel subscription

    Simple, focused agent - CRUD operations only.
    """

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client

        self.stats = {
            "subscriptions_created": 0,
            "subscriptions_deleted": 0,
            "subscriptions_viewed": 0
        }

    async def create_subscription(
        self,
        user_id: str,
        subscription_type: str,
        duration_months: int = 1,
        auto_renew: bool = False
    ) -> str:
        """Create a new subscription"""
        self.stats["subscriptions_created"] += 1

        result = await self.mcp_client.call_tool(
            "create_subscription",
            {
                "user_id": user_id,
                "subscription_type": subscription_type,
                "duration_months": duration_months,
                "auto_renew": auto_renew
            }
        )

        if result.get("status") == "success":
            return f"✅ {result.get('message')}"
        else:
            return f"❌ {result.get('message')}"

    async def get_subscriptions(self, user_id: str) -> str:
        """Get user's subscriptions"""
        self.stats["subscriptions_viewed"] += 1

        result = await self.mcp_client.call_tool(
            "get_user_subscriptions",
            {"user_id": user_id}
        )

        if result.get("status") != "success":
            return f"❌ {result.get('message')}"

        subscriptions = result.get("subscriptions", [])
        if not subscriptions:
            return "📭 Bạn chưa có gói đăng ký nào."

        # Format output
        output = [f"💎 **Gói đăng ký của bạn** ({len(subscriptions)}):\n"]

        for sub in subscriptions:
            status_emoji = "✅" if sub.get('active', False) else "⏸️"
            output.append(
                f"{status_emoji} **{sub.get('type', 'N/A')}**\n"
                f"  • Trạng thái: {sub.get('status', 'N/A')}\n"
                f"  • Hết hạn: {sub.get('expiry_date', 'N/A')}\n"
                f"  • Tự động gia hạn: {'Có' if sub.get('auto_renew', False) else 'Không'}\n"
                f"  • ID: {sub['id']}\n"
            )

        return "\n".join(output)

    async def delete_subscription(self, user_id: str, subscription_id: int) -> str:
        """Cancel a subscription"""
        self.stats["subscriptions_deleted"] += 1

        result = await self.mcp_client.call_tool(
            "delete_subscription",
            {
                "user_id": user_id,
                "subscription_id": subscription_id
            }
        )

        if result.get("status") == "success":
            return f"✅ {result.get('message')}"
        else:
            return f"❌ {result.get('message')}"

    def get_stats(self) -> Dict:
        return self.stats.copy()
