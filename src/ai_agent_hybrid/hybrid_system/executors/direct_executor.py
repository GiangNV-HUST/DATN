"""
Direct Executor - Fast Path for Simple Queries

No agent overhead - just pattern matching and direct tool calls.
Sub-second response time for simple operations.

From OLD system: N/A (didn't have fast path)
From NEW system: Direct tool calling concept
Hybrid: Pattern-based routing to tools
"""

import re
from typing import List, Optional


class DirectExecutor:
    """
    Fast executor for simple queries

    Handles:
    - Price queries
    - Chart requests
    - Alert/subscription CRUD
    - Simple info requests

    No AI reasoning - just parse and execute!
    """

    def __init__(self, mcp_client):
        """
        Initialize Direct Executor

        Args:
            mcp_client: EnhancedMCPClient instance
        """
        self.mcp_client = mcp_client

        # Stats
        self.stats = {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "by_pattern": {}
        }

    async def execute(
        self,
        user_query: str,
        user_id: str,
        suggested_tools: Optional[List[str]] = None
    ) -> str:
        """
        Execute simple query directly

        Args:
            user_query: User's question
            user_id: User ID
            suggested_tools: Tools suggested by AI Router (optional)

        Returns:
            Formatted response string
        """
        self.stats["total_executions"] += 1

        try:
            # Extract symbols from query
            symbols = self._extract_symbols(user_query)
            query_lower = user_query.lower()

            # Pattern matching

            # 1. Price query: "Giá VCB?" or "VCB price"
            if re.search(r'(giá|price)', query_lower) and symbols:
                return await self._handle_price_query(symbols)

            # 2. Chart request: "Biểu đồ VCB" or "VCB chart"
            elif re.search(r'(biểu đồ|chart|đồ thị)', query_lower) and symbols:
                return await self._handle_chart_request(symbols, query_lower)

            # 3. Alert list: "Cảnh báo của tôi" or "My alerts"
            elif re.search(r'(cảnh báo|alert).*( của tôi|của mình|list|danh sách)', query_lower):
                return await self._handle_alert_list(user_id)

            # 4. Subscription list: "Đăng ký của tôi"
            elif re.search(r'(đăng ký|subscription|theo dõi).*( của tôi|của mình|list|danh sách)', query_lower):
                return await self._handle_subscription_list(user_id)

            # 5. Create alert: "Tạo cảnh báo VCB trên 100000"
            elif re.search(r'(tạo|create|thêm|add).*cảnh báo', query_lower) and symbols:
                return await self._handle_create_alert(user_query, user_id, symbols)

            # 6. Delete alert: "Xóa cảnh báo số 5"
            elif re.search(r'(xóa|delete|hủy|remove).*cảnh báo', query_lower):
                return await self._handle_delete_alert(user_query, user_id)

            # 7. Create subscription: "Đăng ký VCB"
            elif re.search(r'(đăng ký|subscribe|theo dõi|follow)', query_lower) and symbols:
                return await self._handle_create_subscription(user_id, symbols)

            # 8. Delete subscription: "Hủy đăng ký VCB"
            elif re.search(r'(hủy|xóa|delete|unsubscribe)', query_lower) and symbols:
                return await self._handle_delete_subscription(user_id, symbols)

            # 9. Financial data: "Tài chính VCB" or "VCB financial"
            elif re.search(r'(tài chính|financial|báo cáo)', query_lower) and symbols:
                return await self._handle_financial_query(symbols)

            # Default: Simple stock info
            elif symbols:
                return await self._handle_price_query(symbols)

            else:
                self.stats["failed"] += 1
                return "❓ Không hiểu câu hỏi. Vui lòng thử lại với format rõ ràng hơn hoặc dùng Agent Mode để phân tích chi tiết."

        except Exception as e:
            self.stats["failed"] += 1
            return f"❌ Lỗi: {str(e)}"

    def _extract_symbols(self, query: str) -> List[str]:
        """Extract stock symbols from query (3 uppercase letters)"""
        symbols = re.findall(r'\b[A-Z]{3}\b', query.upper())
        return list(set(symbols))  # Remove duplicates

    async def _handle_price_query(self, symbols: List[str]) -> str:
        """Handle price queries"""
        self._record_pattern("price_query")

        try:
            result = await self.mcp_client.get_stock_data(
                symbols=symbols,
                lookback_days=1
            )

            if result.get("status") != "success":
                return f"❌ Lỗi: {result.get('message', 'Unknown error')}"

            # Format response
            response_parts = ["📊 **Thông tin giá:**\n"]

            results = result.get("results", {})
            for symbol in symbols:
                data = results.get(symbol, [])
                if data and len(data) > 0:
                    latest = data[0]

                    price = latest.get("close", 0)
                    change_pct = latest.get("percent_price_change", 0)
                    volume = latest.get("volume", 0)

                    emoji = "🟢" if change_pct >= 0 else "🔴"

                    response_parts.append(
                        f"{emoji} **{symbol}**: {price:,.0f} VNĐ ({change_pct:+.2f}%)\n"
                        f"   Khối lượng: {volume:,.0f}"
                    )
                else:
                    response_parts.append(f"⚠️ **{symbol}**: Không có dữ liệu")

            self.stats["successful"] += 1
            return "\n".join(response_parts)

        except Exception as e:
            return f"❌ Lỗi: {str(e)}"

    async def _handle_chart_request(self, symbols: List[str], query: str) -> str:
        """Handle chart generation requests"""
        self._record_pattern("chart_request")

        try:
            # Extract timeframe from query
            lookback_days = 30  # default
            if "7" in query or "tuần" in query:
                lookback_days = 7
            elif "90" in query or "quý" in query:
                lookback_days = 90

            result = await self.mcp_client.generate_chart_from_data(
                symbols=symbols,
                lookback_days=lookback_days
            )

            if result.get("status") != "success":
                return f"❌ Lỗi: {result.get('message')}"

            chart_paths = result.get("chart_paths", {})

            response_parts = ["📈 **Biểu đồ đã tạo:**\n"]
            for symbol, path in chart_paths.items():
                response_parts.append(f"✅ {symbol}: {path}")

            self.stats["successful"] += 1
            return "\n".join(response_parts)

        except Exception as e:
            return f"❌ Lỗi: {str(e)}"

    async def _handle_alert_list(self, user_id: str) -> str:
        """Handle alert list query"""
        self._record_pattern("alert_list")

        try:
            result = await self.mcp_client.get_user_alerts(user_id=user_id)

            if result.get("status") != "success":
                return f"❌ Lỗi: {result.get('message')}"

            alerts = result.get("alerts", [])

            if not alerts:
                return "📭 Bạn chưa có cảnh báo nào."

            response_parts = [f"🔔 **Cảnh báo của bạn** ({len(alerts)}):\n"]

            for alert in alerts:
                response_parts.append(
                    f"• **{alert['symbol']}** - {alert.get('description', 'N/A')}\n"
                    f"  ID: {alert['id']} | Tạo: {alert.get('created_at', 'N/A')}"
                )

            self.stats["successful"] += 1
            return "\n".join(response_parts)

        except Exception as e:
            return f"❌ Lỗi: {str(e)}"

    async def _handle_subscription_list(self, user_id: str) -> str:
        """Handle subscription list query"""
        self._record_pattern("subscription_list")

        try:
            result = await self.mcp_client.get_user_subscriptions(user_id=user_id)

            if result.get("status") != "success":
                return f"❌ Lỗi: {result.get('message')}"

            subs = result.get("subscriptions", [])

            if not subs:
                return "📭 Bạn chưa theo dõi cổ phiếu nào."

            response_parts = [f"📌 **Cổ phiếu đang theo dõi** ({len(subs)}):\n"]

            symbols = [sub['symbol'] for sub in subs]
            response_parts.append("• " + ", ".join(symbols))

            self.stats["successful"] += 1
            return "\n".join(response_parts)

        except Exception as e:
            return f"❌ Lỗi: {str(e)}"

    async def _handle_create_alert(self, query: str, user_id: str, symbols: List[str]) -> str:
        """Handle create alert"""
        self._record_pattern("create_alert")

        # Parse condition and value
        # Example: "Tạo cảnh báo VCB trên 100000"
        match = re.search(r'(trên|trước|dưới|above|below)\s+([\d,\.]+)', query.lower())
        if not match or not symbols:
            return "❓ Không hiểu cú pháp. Ví dụ: 'Tạo cảnh báo VCB trên 100000'"

        condition_text = match.group(1)
        condition = "above" if condition_text in ["trên", "above"] else "below"
        value = float(match.group(2).replace(",", "").replace(".", ""))

        try:
            result = await self.mcp_client.create_alert(
                user_id=user_id,
                symbol=symbols[0],
                alert_type="price",
                target_value=value,
                condition=condition
            )

            if result.get("status") == "success":
                self.stats["successful"] += 1
                return f"✅ {result.get('message')}"
            else:
                return f"❌ {result.get('message')}"

        except Exception as e:
            return f"❌ Lỗi: {str(e)}"

    async def _handle_delete_alert(self, query: str, user_id: str) -> str:
        """Handle delete alert"""
        self._record_pattern("delete_alert")

        # Extract alert ID
        match = re.search(r'(\d+)', query)
        if not match:
            return "❓ Vui lòng cung cấp ID cảnh báo. Ví dụ: 'Xóa cảnh báo số 5'"

        alert_id = int(match.group(1))

        try:
            result = await self.mcp_client.delete_alert(
                user_id=user_id,
                alert_id=alert_id
            )

            if result.get("status") == "success":
                self.stats["successful"] += 1
                return f"✅ {result.get('message')}"
            else:
                return f"❌ {result.get('message')}"

        except Exception as e:
            return f"❌ Lỗi: {str(e)}"

    async def _handle_create_subscription(self, user_id: str, symbols: List[str]) -> str:
        """Handle create subscription"""
        self._record_pattern("create_subscription")

        try:
            result = await self.mcp_client.create_subscription(
                user_id=user_id,
                symbol=symbols[0]
            )

            if result.get("status") == "success":
                self.stats["successful"] += 1
                return f"✅ {result.get('message')}"
            else:
                return f"❌ {result.get('message')}"

        except Exception as e:
            return f"❌ Lỗi: {str(e)}"

    async def _handle_delete_subscription(self, user_id: str, symbols: List[str]) -> str:
        """Handle delete subscription"""
        self._record_pattern("delete_subscription")

        # Need to get subscription ID first
        try:
            # Get all subscriptions
            result = await self.mcp_client.get_user_subscriptions(user_id=user_id)

            if result.get("status") != "success":
                return f"❌ Lỗi: {result.get('message')}"

            subs = result.get("subscriptions", [])

            # Find subscription for this symbol
            sub_id = None
            for sub in subs:
                if sub['symbol'] == symbols[0]:
                    sub_id = sub['id']
                    break

            if sub_id is None:
                return f"⚠️ Bạn chưa theo dõi {symbols[0]}"

            # Delete subscription
            result = await self.mcp_client.delete_subscription(
                user_id=user_id,
                subscription_id=sub_id
            )

            if result.get("status") == "success":
                self.stats["successful"] += 1
                return f"✅ {result.get('message')}"
            else:
                return f"❌ {result.get('message')}"

        except Exception as e:
            return f"❌ Lỗi: {str(e)}"

    async def _handle_financial_query(self, symbols: List[str]) -> str:
        """Handle financial data query"""
        self._record_pattern("financial_query")

        try:
            result = await self.mcp_client.get_financial_data(
                tickers=symbols,
                is_income_statement=True,
                period="quarterly",
                num_periods=4
            )

            if result.get("status") != "success":
                return f"❌ Lỗi: {result.get('message')}"

            response_parts = ["💰 **Báo cáo tài chính:**\n"]

            results = result.get("results", {})
            for symbol in symbols:
                data = results.get(symbol, {})
                income_stmt = data.get("income_statement", [])

                if income_stmt and len(income_stmt) > 0:
                    latest = income_stmt[0]
                    revenue = latest.get("revenue", 0)
                    profit = latest.get("net_profit", 0)

                    response_parts.append(
                        f"📊 **{symbol}**:\n"
                        f"  Doanh thu: {revenue:,.0f} tỷ\n"
                        f"  Lợi nhuận: {profit:,.0f} tỷ"
                    )
                else:
                    response_parts.append(f"⚠️ **{symbol}**: Không có dữ liệu")

            self.stats["successful"] += 1
            return "\n".join(response_parts)

        except Exception as e:
            return f"❌ Lỗi: {str(e)}"

    def _record_pattern(self, pattern_name: str):
        """Record which pattern was used"""
        if pattern_name not in self.stats["by_pattern"]:
            self.stats["by_pattern"][pattern_name] = 0
        self.stats["by_pattern"][pattern_name] += 1

    def get_stats(self):
        """Get executor statistics"""
        total = self.stats["total_executions"]
        success_rate = (
            f"{self.stats['successful'] / total * 100:.1f}%"
            if total > 0 else "0%"
        )

        return {
            **self.stats,
            "success_rate": success_rate
        }
