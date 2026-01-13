"""
Streamlit UI for Stock Advisor with OpenAI

This version uses OpenAI API instead of the complex HybridOrchestrator agent system.
Perfect for quick setup and testing.

Run with: streamlit run src/streamlit_ui/app_openai.py
"""

import streamlit as st
import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.streamlit_ui import config
from src.streamlit_ui.utils import get_openai_client, get_session_manager, ResponseFormatter

# Page configuration
st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout=config.LAYOUT,
    initial_sidebar_state=config.INITIAL_SIDEBAR_STATE
)

# Initialize managers (MUST be after set_page_config)
session_manager = get_session_manager()
session_manager._initialize_session_state()  # Ensure session state is initialized
formatter = ResponseFormatter()

# Initialize OpenAI client (will be created on first use)
openai_client = None


def get_client():
    """Get or create OpenAI client."""
    global openai_client
    if openai_client is None:
        try:
            openai_client = get_openai_client()
            st.success("✅ Đã kết nối với OpenAI")
        except ValueError as e:
            st.error(f"❌ Lỗi: {str(e)}")
            st.info("Vui lòng set OPENAI_API_KEY trong file .env")
            st.stop()
    return openai_client


def render_sidebar():
    """Render sidebar."""
    with st.sidebar:
        st.title("📈 Stock Advisor AI")
        st.caption("Powered by OpenAI")

        # Session info
        st.markdown("---")
        st.markdown("### 👤 Session Info")
        st.caption(f"**Session:** {session_manager.get_session_id()[:8]}...")
        st.caption(f"**User:** {session_manager.get_user_id()}")

        # Conversation summary
        summary = session_manager.get_conversation_summary()
        st.caption(f"**Hội thoại:** {summary}")

        # Quick actions
        st.markdown("---")
        st.markdown("### ⚡ Thao tác nhanh")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🆕 Chat mới", use_container_width=True):
                session_manager.clear_messages()
                st.rerun()

        with col2:
            if st.button("♻️ Reset", use_container_width=True):
                session_manager.reset_session()
                st.rerun()

        # Model settings
        st.markdown("---")
        st.markdown("### 🤖 Model Settings")

        current_model = config.OPENAI_MODEL
        st.caption(f"**Current Model:** {current_model}")

        # About
        st.markdown("---")
        st.markdown("### ℹ️ Về hệ thống")
        st.caption("""
        **Stock Advisor AI (OpenAI Version)**

        Hệ thống tư vấn đầu tư chứng khoán sử dụng:
        - 🤖 OpenAI GPT models
        - 💬 Natural conversation
        - 📊 Stock market knowledge
        - 🇻🇳 Vietnamese language support

        Version 1.0.0 (OpenAI)
        """)


def render_chat_message(message):
    """Render a single chat message."""
    with st.chat_message(message.role):
        st.markdown(message.content)

        # Show metadata if available
        if message.metadata:
            with st.expander("📋 Chi tiết", expanded=False):
                if "usage" in message.metadata:
                    usage = message.metadata["usage"]
                    cols = st.columns(3)
                    cols[0].metric("Prompt tokens", usage.get("prompt_tokens", 0))
                    cols[1].metric("Completion tokens", usage.get("completion_tokens", 0))
                    cols[2].metric("Total tokens", usage.get("total_tokens", 0))

                if "model" in message.metadata:
                    st.caption(f"🤖 Model: {message.metadata['model']}")


async def process_user_query(user_input: str):
    """Process user query through OpenAI."""

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

            # Get OpenAI client
            client = get_client()

            # Get conversation history (last 10 messages for context)
            messages = session_manager.get_messages()
            history = []
            for msg in messages[-10:]:  # Last 10 messages
                if msg.role in ["user", "assistant"]:
                    history.append({
                        "role": msg.role,
                        "content": msg.content
                    })

            # Call OpenAI
            result = await client.chat(
                user_message=user_input,
                conversation_history=history[:-1],  # Exclude current message
                temperature=0.7
            )

            # Get response
            response_text = result.get("response", "")

            # Update message placeholder
            message_placeholder.markdown(response_text)

            # Add to history with metadata
            session_manager.add_message(
                "assistant",
                response_text,
                metadata={
                    "usage": result.get("usage", {}),
                    "model": result.get("model", ""),
                    "finish_reason": result.get("finish_reason", "")
                }
            )

        except Exception as e:
            error_msg = f"❌ Đã có lỗi xảy ra: {str(e)}"
            message_placeholder.markdown(error_msg)
            session_manager.add_message("assistant", error_msg)

        finally:
            session_manager.set_processing(False)


def main():
    """Main application."""

    # Header
    st.title("📈 Stock Advisor AI")
    st.caption("Hệ thống tư vấn đầu tư chứng khoán thông minh - Powered by OpenAI")

    # Sidebar
    render_sidebar()

    # Main chat interface
    st.markdown("---")

    # Display conversation history
    messages = session_manager.get_messages()

    if not messages:
        # Welcome message
        st.info("""
        👋 **Chào mừng bạn đến với Stock Advisor AI!**

        Tôi là trợ lý AI chuyên về tư vấn đầu tư chứng khoán. Tôi có thể giúp bạn:
        - 📊 Giải thích các khái niệm đầu tư
        - 💼 Tư vấn chiến lược đầu tư
        - 🔍 Phân tích xu hướng thị trường
        - 📈 Giải đáp thắc mắc về chứng khoán Việt Nam

        **Ví dụ câu hỏi:**
        - "Giải thích P/E ratio là gì?"
        - "Cổ phiếu ngân hàng đang có xu hướng như thế nào?"
        - "Chiến lược đầu tư dài hạn là gì?"
        - "Nên đa dạng hóa danh mục như thế nào?"

        **Lưu ý:** Đây là thông tin tham khảo. Hãy tự nghiên cứu kỹ trước khi đầu tư.
        """)
    else:
        # Render all messages
        for message in messages:
            render_chat_message(message)

    # Chat input
    if user_input := st.chat_input(
        "Hỏi về đầu tư, phân tích thị trường, hoặc chiến lược...",
        disabled=session_manager.is_processing()
    ):
        # Run async query processing
        asyncio.run(process_user_query(user_input))
        st.rerun()


if __name__ == "__main__":
    main()
