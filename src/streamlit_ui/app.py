"""
Main Streamlit UI for Stock Advisor AI Agent System

Run with: streamlit run src/streamlit_ui/app.py
"""

import streamlit as st
import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.streamlit_ui import config
from src.streamlit_ui.utils import get_agent_bridge, get_session_manager, ResponseFormatter
from src.streamlit_ui.components import render_sidebar, render_metrics_panel

# Page configuration
st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout=config.LAYOUT,
    initial_sidebar_state=config.INITIAL_SIDEBAR_STATE
)

# Initialize managers
session_manager = get_session_manager()
agent_bridge = get_agent_bridge()
formatter = ResponseFormatter()


def render_chat_message(message):
    """Render a single chat message."""
    with st.chat_message(message.role):
        st.markdown(message.content)

        # Show metadata if available and setting enabled
        if session_manager.get_setting("show_metrics", True) and message.metadata:
            with st.expander("Chi tiết", expanded=False):
                cols = st.columns(3)

                if "mode" in message.metadata:
                    mode = message.metadata["mode"]
                    mode_emoji = "🤖" if mode == "agent" else "⚡"
                    cols[0].metric("Mode", f"{mode_emoji} {mode.upper()}")

                if "execution_time" in message.metadata:
                    exec_time = message.metadata["execution_time"]
                    cols[1].metric("Thời gian", f"{exec_time:.2f}s")

                if "tools_used" in message.metadata:
                    tools = message.metadata["tools_used"]
                    if tools:
                        cols[2].metric("Tools", len(tools))
                        st.caption(f"🔧 {', '.join(tools[:3])}{'...' if len(tools) > 3 else ''}")


async def process_user_query(user_input: str):
    """Process user query through agent system."""

    # Add user message to history
    session_manager.add_message("user", user_input)

    # Show user message
    with st.chat_message("user"):
        st.markdown(user_input)

    # Show assistant thinking
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🤔 Đang suy nghĩ...")

        try:
            # Set processing state
            session_manager.set_processing(True)

            # Process query through agent bridge
            result = await agent_bridge.process_query(
                user_query=user_input,
                user_id=session_manager.get_user_id(),
                session_id=session_manager.get_session_id(),
                enable_streaming=session_manager.get_setting("enable_streaming", True)
            )

            # Format response
            formatted_response = formatter.format_agent_response(result)

            # Update message placeholder
            message_placeholder.markdown(formatted_response)

            # Add to history with metadata
            session_manager.add_message(
                "assistant",
                formatted_response,
                metadata={
                    "mode": result.get("mode"),
                    "execution_time": result.get("execution_time"),
                    "tools_used": result.get("tools_used", [])
                }
            )

            # Update metrics
            if config.ENABLE_METRICS_DASHBOARD:
                metrics = agent_bridge.get_metrics()
                session_manager.update_metrics(metrics)

        except Exception as e:
            error_msg = f"❌ Đã có lỗi xảy ra: {str(e)}"
            message_placeholder.markdown(error_msg)
            session_manager.add_message("assistant", error_msg)

        finally:
            session_manager.set_processing(False)


def main():
    """Main application."""

    # Header
    st.title("📈 Stock Advisor AI Agent")
    st.caption("Hệ thống tư vấn đầu tư chứng khoán thông minh với Multi-Agent AI")

    # Sidebar
    render_sidebar(session_manager, agent_bridge)

    # Main chat interface
    st.markdown("---")

    # Display conversation history
    messages = session_manager.get_messages()

    if not messages:
        # Welcome message
        st.info("""
        👋 **Chào mừng bạn đến với Stock Advisor AI!**

        Tôi có thể giúp bạn:
        - 📊 Phân tích cổ phiếu (kỹ thuật, tài chính, tin tức)
        - 💼 Tư vấn đầu tư và phân bổ danh mục
        - 🔍 Tìm kiếm cổ phiếu tiềm năng
        - 🔔 Quản lý cảnh báo giá
        - 📈 Dự đoán xu hướng giá

        **Ví dụ câu hỏi:**
        - "Phân tích cổ phiếu VCB"
        - "Tư vấn đầu tư 100 triệu vào ngành ngân hàng"
        - "So sánh VCB với TCB"
        - "Tạo cảnh báo khi VCB vượt 100k"
        """)
    else:
        # Render all messages
        for message in messages:
            render_chat_message(message)

    # Chat input
    if user_input := st.chat_input(
        "Hỏi về cổ phiếu, phân tích, hoặc tư vấn đầu tư...",
        disabled=session_manager.is_processing()
    ):
        # Run async query processing
        asyncio.run(process_user_query(user_input))
        st.rerun()

    # Metrics panel (optional)
    if config.ENABLE_METRICS_DASHBOARD and session_manager.get_setting("show_metrics", True):
        with st.expander("📊 System Metrics", expanded=False):
            render_metrics_panel(session_manager)


if __name__ == "__main__":
    main()
