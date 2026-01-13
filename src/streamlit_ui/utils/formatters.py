"""
Formatters for agent responses and data visualization.
"""

from typing import Dict, Any
import re


class ResponseFormatter:
    """Format agent responses for better display in Streamlit."""

    @staticmethod
    def format_agent_response(result: Dict[str, Any]) -> str:
        """
        Format agent response with metadata.

        Args:
            result: Result dict from agent system

        Returns:
            Formatted string for display
        """
        response_text = result.get("response", "")
        mode = result.get("mode", "unknown")
        execution_time = result.get("execution_time", 0)
        tools_used = result.get("tools_used", [])

        # Main response
        formatted = response_text

        # Add metadata footer if available
        if mode != "error" and (mode or execution_time or tools_used):
            formatted += "\n\n---\n"
            formatted += "**Thông tin xử lý:**\n"

            if mode:
                mode_emoji = "🤖" if mode == "agent" else "⚡"
                mode_text = "Agent Mode (phân tích phức tạp)" if mode == "agent" else "Direct Mode (truy vấn nhanh)"
                formatted += f"- {mode_emoji} Mode: {mode_text}\n"

            if execution_time:
                formatted += f"- ⏱️ Thời gian: {execution_time:.2f}s\n"

            if tools_used:
                formatted += f"- 🔧 Tools: {', '.join(tools_used)}\n"

        return formatted

    @staticmethod
    def format_stock_price(price: float, currency: str = "VND") -> str:
        """Format stock price with thousands separator."""
        if currency == "VND":
            return f"{price:,.0f} đ"
        return f"{price:,.2f}"

    @staticmethod
    def format_percentage(value: float) -> str:
        """Format percentage with + or - sign."""
        sign = "+" if value >= 0 else ""
        return f"{sign}{value:.2f}%"

    @staticmethod
    def format_alert_condition(condition: str) -> str:
        """Format alert condition for display."""
        condition_map = {
            "above": "Trên",
            "below": "Dưới",
            "crosses_above": "Vượt lên",
            "crosses_below": "Vượt xuống"
        }
        return condition_map.get(condition, condition)

    @staticmethod
    def extract_stock_symbols(text: str) -> list:
        """
        Extract stock symbols from text.
        Looks for 3-letter uppercase codes (Vietnamese stock pattern).
        """
        pattern = r'\b[A-Z]{3}\b'
        symbols = re.findall(pattern, text)
        return list(set(symbols))  # Remove duplicates

    @staticmethod
    def format_large_number(number: float) -> str:
        """
        Format large numbers with K, M, B suffixes.

        Args:
            number: Number to format

        Returns:
            Formatted string (e.g., "1.5M", "100K")
        """
        if number >= 1_000_000_000:
            return f"{number / 1_000_000_000:.1f}B"
        elif number >= 1_000_000:
            return f"{number / 1_000_000:.1f}M"
        elif number >= 1_000:
            return f"{number / 1_000:.1f}K"
        else:
            return f"{number:.0f}"

    @staticmethod
    def truncate_text(text: str, max_length: int = 100) -> str:
        """
        Truncate text to max length with ellipsis.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    @staticmethod
    def format_timestamp(timestamp: Any) -> str:
        """
        Format timestamp for display.

        Args:
            timestamp: Timestamp (datetime, string, or float)

        Returns:
            Formatted time string
        """
        from datetime import datetime

        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp)
            except ValueError:
                return timestamp
        elif isinstance(timestamp, float):
            dt = datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, datetime):
            dt = timestamp
        else:
            return str(timestamp)

        # Format as "HH:MM DD/MM/YYYY"
        return dt.strftime("%H:%M %d/%m/%Y")

    @staticmethod
    def colorize_change(value: float) -> str:
        """
        Return color based on value (for price changes).

        Args:
            value: Change value

        Returns:
            Color name for Streamlit
        """
        if value > 0:
            return "green"
        elif value < 0:
            return "red"
        else:
            return "gray"
