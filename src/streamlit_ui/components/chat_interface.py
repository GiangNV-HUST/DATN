"""
Chat interface components
"""

import streamlit as st


def render_chat_message(message):
    """
    Render a single chat message with metadata.

    Args:
        message: Message object with role, content, and metadata
    """
    with st.chat_message(message.role):
        st.markdown(message.content)

        # Show metadata if available
        if message.metadata:
            with st.expander("📋 Chi tiết", expanded=False):
                cols = st.columns(3)

                if "mode" in message.metadata:
                    mode = message.metadata["mode"]
                    mode_emoji = "🤖" if mode == "agent" else "⚡"
                    mode_text = "Agent" if mode == "agent" else "Direct"
                    cols[0].metric("Mode", f"{mode_emoji} {mode_text}")

                if "execution_time" in message.metadata:
                    exec_time = message.metadata["execution_time"]
                    cols[1].metric("Thời gian", f"{exec_time:.2f}s")

                if "tools_used" in message.metadata:
                    tools = message.metadata["tools_used"]
                    if tools:
                        cols[2].metric("Tools", len(tools))
                        st.caption(f"🔧 {', '.join(tools[:3])}{'...' if len(tools) > 3 else ''}")


def render_suggested_questions():
    """Render suggested questions for user."""
    st.markdown("### 💡 Câu hỏi gợi ý")

    suggestions = [
        "📊 Phân tích cổ phiếu VCB",
        "💼 Tư vấn đầu tư 100 triệu",
        "🔍 Tìm cổ phiếu ngành công nghệ tốt",
        "📈 Dự báo giá VCB 3 ngày tới",
        "🔔 Tạo cảnh báo VCB > 100k"
    ]

    cols = st.columns(2)
    for i, suggestion in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(suggestion, key=f"suggest_{i}", use_container_width=True):
                return suggestion.split(" ", 1)[1]  # Remove emoji

    return None


def render_quick_actions():
    """Render quick action buttons."""
    st.markdown("### ⚡ Thao tác nhanh")

    cols = st.columns(3)

    with cols[0]:
        if st.button("🔔 Cảnh báo của tôi", use_container_width=True):
            return "show_alerts"

    with cols[1]:
        if st.button("💼 Danh mục đầu tư", use_container_width=True):
            return "show_portfolio"

    with cols[2]:
        if st.button("📊 Metrics", use_container_width=True):
            return "show_metrics"

    return None
