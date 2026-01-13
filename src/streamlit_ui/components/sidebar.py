"""
Sidebar component with portfolio, alerts, and settings
"""

import streamlit as st
import asyncio


def render_sidebar(session_manager, agent_bridge):
    """
    Render sidebar with portfolio overview, alerts, and settings.

    Args:
        session_manager: SessionManager instance
        agent_bridge: AgentBridge instance
    """

    with st.sidebar:
        st.title("📈 Stock Advisor AI")

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

        # Portfolio overview
        st.markdown("---")
        st.markdown("### 💼 Portfolio Overview")

        if st.button("🔄 Refresh Portfolio", use_container_width=True):
            with st.spinner("Đang tải..."):
                try:
                    portfolio_data = asyncio.run(
                        agent_bridge.get_portfolio_overview(
                            session_manager.get_user_id()
                        )
                    )
                    session_manager.update_portfolio_cache(portfolio_data)
                    st.success("✅ Đã cập nhật!")
                except Exception as e:
                    st.error(f"❌ Lỗi: {str(e)}")

        # Display cached portfolio data
        portfolio_data = session_manager.get_portfolio_cache()
        if portfolio_data:
            # Alerts
            alerts = portfolio_data.get("alerts", [])
            st.metric("🔔 Cảnh báo", len(alerts))

            if alerts:
                with st.expander(f"Xem {len(alerts)} cảnh báo", expanded=False):
                    for alert in alerts[:5]:  # Show first 5
                        st.caption(f"• {alert.get('symbol', 'N/A')} - {alert.get('condition', 'N/A')}")

            # Subscriptions
            subs = portfolio_data.get("subscriptions", [])
            st.metric("📊 Theo dõi", len(subs))

            if subs:
                with st.expander(f"Xem {len(subs)} cổ phiếu", expanded=False):
                    for sub in subs[:5]:  # Show first 5
                        st.caption(f"• {sub.get('symbol', 'N/A')}")
        else:
            st.info("Chưa có dữ liệu portfolio. Click 'Refresh Portfolio' để tải.")

        # Settings
        st.markdown("---")
        st.markdown("### ⚙️ Cài đặt")

        # Streaming toggle
        enable_streaming = st.toggle(
            "Real-time streaming",
            value=session_manager.get_setting("enable_streaming", True),
            help="Hiển thị tiến trình xử lý real-time"
        )
        session_manager.update_setting("enable_streaming", enable_streaming)

        # Metrics toggle
        show_metrics = st.toggle(
            "Hiển thị metrics",
            value=session_manager.get_setting("show_metrics", True),
            help="Hiển thị thông tin chi tiết về xử lý"
        )
        session_manager.update_setting("show_metrics", show_metrics)

        # About
        st.markdown("---")
        st.markdown("### ℹ️ Về hệ thống")
        st.caption("""
        **Stock Advisor AI Agent**

        Hệ thống Multi-Agent thông minh với:
        - 🤖 AI Routing (Agent/Direct mode)
        - 📊 5-Model Ensemble Prediction
        - 🔧 25+ MCP Tools
        - 💾 Intelligent Caching
        - ⚡ Sub-second responses

        Version 1.0.0
        """)


def render_alert_manager(agent_bridge, session_manager):
    """
    Render alert management interface.

    Args:
        agent_bridge: AgentBridge instance
        session_manager: SessionManager instance
    """

    st.markdown("### 🔔 Quản lý Cảnh báo")

    # Create new alert form
    with st.expander("➕ Tạo cảnh báo mới", expanded=False):
        with st.form("create_alert_form"):
            col1, col2 = st.columns(2)

            with col1:
                symbol = st.text_input("Mã cổ phiếu", placeholder="VCB").upper()
                condition = st.selectbox(
                    "Điều kiện",
                    options=["above", "below", "crosses_above", "crosses_below"],
                    format_func=lambda x: {
                        "above": "Trên",
                        "below": "Dưới",
                        "crosses_above": "Vượt lên",
                        "crosses_below": "Vượt xuống"
                    }[x]
                )

            with col2:
                target_price = st.number_input(
                    "Giá mục tiêu (VND)",
                    min_value=0.0,
                    value=100000.0,
                    step=1000.0
                )
                alert_type = st.selectbox(
                    "Loại",
                    options=["price", "volume", "indicator"],
                    format_func=lambda x: {
                        "price": "Giá",
                        "volume": "Khối lượng",
                        "indicator": "Chỉ báo"
                    }[x]
                )

            submitted = st.form_submit_button("Tạo cảnh báo", use_container_width=True)

            if submitted:
                if not symbol:
                    st.error("Vui lòng nhập mã cổ phiếu!")
                else:
                    with st.spinner("Đang tạo..."):
                        try:
                            result = asyncio.run(
                                agent_bridge.create_alert(
                                    user_id=session_manager.get_user_id(),
                                    symbol=symbol,
                                    condition=condition,
                                    target_price=target_price,
                                    alert_type=alert_type
                                )
                            )

                            if result.get("success"):
                                st.success(f"✅ Đã tạo cảnh báo cho {symbol}!")
                                # Refresh cache
                                asyncio.run(
                                    agent_bridge.get_user_alerts(
                                        session_manager.get_user_id()
                                    )
                                )
                            else:
                                st.error(f"❌ Lỗi: {result.get('error', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"❌ Lỗi: {str(e)}")

    # List existing alerts
    st.markdown("### 📋 Danh sách cảnh báo")

    try:
        alerts = asyncio.run(
            agent_bridge.get_user_alerts(session_manager.get_user_id())
        )

        if not alerts:
            st.info("Chưa có cảnh báo nào.")
        else:
            for alert in alerts:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])

                    with col1:
                        st.markdown(f"**{alert.get('symbol', 'N/A')}**")
                        st.caption(f"{alert.get('condition', 'N/A')} {alert.get('target_price', 0):,.0f}")

                    with col2:
                        st.caption(f"Type: {alert.get('alert_type', 'N/A')}")
                        status = alert.get('status', 'active')
                        status_emoji = "✅" if status == "active" else "⏸️"
                        st.caption(f"Status: {status_emoji} {status}")

                    with col3:
                        if st.button("🗑️", key=f"del_{alert.get('id')}"):
                            try:
                                asyncio.run(
                                    agent_bridge.delete_alert(alert.get('id'))
                                )
                                st.success("Đã xóa!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi: {str(e)}")

                    st.markdown("---")

    except Exception as e:
        st.error(f"Không thể tải cảnh báo: {str(e)}")
