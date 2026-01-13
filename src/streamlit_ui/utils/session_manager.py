"""
Session state management for Streamlit UI.
Manages conversation history, user sessions, and UI state.
"""

import streamlit as st
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Message:
    """Represents a chat message."""

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.role = role  # "user" or "assistant"
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class SessionManager:
    """
    Manages Streamlit session state and conversation history.
    """

    def __init__(self):
        self._initialize_session_state()

    def _initialize_session_state(self):
        """Initialize session state variables if not present."""

        # Session ID
        if "session_id" not in st.session_state:
            st.session_state.session_id = f"streamlit_{uuid.uuid4().hex[:8]}"

        # User ID
        if "user_id" not in st.session_state:
            st.session_state.user_id = "streamlit_user"

        # Conversation history
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Agent metrics
        if "agent_metrics" not in st.session_state:
            st.session_state.agent_metrics = {}

        # UI state
        if "processing" not in st.session_state:
            st.session_state.processing = False

        # Last activity timestamp
        if "last_activity" not in st.session_state:
            st.session_state.last_activity = datetime.now()

        # Portfolio data cache
        if "portfolio_data" not in st.session_state:
            st.session_state.portfolio_data = None

        # Alerts cache
        if "alerts_cache" not in st.session_state:
            st.session_state.alerts_cache = []

        # Settings
        if "settings" not in st.session_state:
            st.session_state.settings = {
                "enable_streaming": True,
                "show_metrics": True,
                "theme": "light"
            }

    def get_session_id(self) -> str:
        """Get current session ID."""
        return st.session_state.session_id

    def get_user_id(self) -> str:
        """Get current user ID."""
        return st.session_state.user_id

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a message to conversation history.

        Args:
            role: "user" or "assistant"
            content: Message content
            metadata: Optional metadata (mode, execution_time, etc.)
        """
        message = Message(role, content, metadata=metadata)
        st.session_state.messages.append(message)
        st.session_state.last_activity = datetime.now()

    def get_messages(self) -> List[Message]:
        """Get all messages in conversation history."""
        return st.session_state.messages

    def clear_messages(self):
        """Clear conversation history."""
        st.session_state.messages = []
        logger.info(f"Cleared conversation history for session {self.get_session_id()}")

    def update_metrics(self, metrics: Dict[str, Any]):
        """Update agent metrics."""
        st.session_state.agent_metrics = metrics
        st.session_state.last_activity = datetime.now()

    def get_metrics(self) -> Dict[str, Any]:
        """Get current agent metrics."""
        return st.session_state.agent_metrics

    def set_processing(self, is_processing: bool):
        """Set processing state."""
        st.session_state.processing = is_processing

    def is_processing(self) -> bool:
        """Check if currently processing."""
        return st.session_state.processing

    def update_portfolio_cache(self, portfolio_data: Dict[str, Any]):
        """Update cached portfolio data."""
        st.session_state.portfolio_data = portfolio_data
        st.session_state.last_activity = datetime.now()

    def get_portfolio_cache(self) -> Optional[Dict[str, Any]]:
        """Get cached portfolio data."""
        return st.session_state.portfolio_data

    def update_alerts_cache(self, alerts: List[Dict[str, Any]]):
        """Update cached alerts."""
        st.session_state.alerts_cache = alerts
        st.session_state.last_activity = datetime.now()

    def get_alerts_cache(self) -> List[Dict[str, Any]]:
        """Get cached alerts."""
        return st.session_state.alerts_cache

    def get_setting(self, key: str, default=None):
        """Get a setting value."""
        return st.session_state.settings.get(key, default)

    def update_setting(self, key: str, value):
        """Update a setting."""
        st.session_state.settings[key] = value

    def is_session_expired(self, timeout_minutes: int = 30) -> bool:
        """
        Check if session has expired due to inactivity.

        Args:
            timeout_minutes: Session timeout in minutes

        Returns:
            True if session expired, False otherwise
        """
        last_activity = st.session_state.last_activity
        timeout = timedelta(minutes=timeout_minutes)
        return datetime.now() - last_activity > timeout

    def reset_session(self):
        """Reset entire session state."""
        keys_to_keep = ["session_id", "user_id"]

        # Clear all except keys to keep
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]

        # Re-initialize
        self._initialize_session_state()

        logger.info(f"Reset session {self.get_session_id()}")

    def get_conversation_summary(self) -> str:
        """
        Get a summary of the conversation.

        Returns:
            Summary string with message count and topics
        """
        messages = self.get_messages()

        if not messages:
            return "Chưa có tin nhắn nào"

        user_msgs = sum(1 for m in messages if m.role == "user")
        assistant_msgs = sum(1 for m in messages if m.role == "assistant")

        return f"{len(messages)} tin nhắn ({user_msgs} từ bạn, {assistant_msgs} từ AI)"


# Singleton instance
_session_manager = None


def get_session_manager() -> SessionManager:
    """Get or create singleton SessionManager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
