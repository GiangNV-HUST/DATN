"""
Configuration for Streamlit UI
"""

import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
AGENT_SYSTEM_PATH = PROJECT_ROOT / "src" / "ai_agent_hybrid" / "hybrid_system"

# UI Settings
PAGE_TITLE = "Stock Advisor AI Agent"
PAGE_ICON = "📈"
LAYOUT = "wide"
INITIAL_SIDEBAR_STATE = "expanded"

# Session Settings
SESSION_TIMEOUT_MINUTES = 30
MAX_CONVERSATION_HISTORY = 50

# Agent Settings
DEFAULT_USER_ID = "streamlit_user"
ENABLE_STREAMING = True
ENABLE_DEBUG_MODE = False

# Visual Settings
PRIMARY_COLOR = "#1f77b4"
BACKGROUND_COLOR = "#ffffff"
SECONDARY_BACKGROUND_COLOR = "#f0f2f6"
TEXT_COLOR = "#262730"

# Chart Settings
CHART_HEIGHT = 400
CHART_THEME = "streamlit"

# API Keys (load from environment)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # or "gpt-4o", "gpt-3.5-turbo"

# Feature Flags
ENABLE_PORTFOLIO_PAGE = True
ENABLE_ALERTS_PAGE = True
ENABLE_SETTINGS_PAGE = True
ENABLE_METRICS_DASHBOARD = True
