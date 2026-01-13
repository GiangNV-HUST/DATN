"""
System metrics dashboard component
"""

import streamlit as st
from typing import Dict, Any


def render_metrics_panel(session_manager):
    """
    Render system metrics panel.

    Args:
        session_manager: SessionManager instance
    """

    metrics = session_manager.get_metrics()

    if not metrics:
        st.info("Chưa có dữ liệu metrics. Hãy thử chat với agent!")
        return

    # Main metrics
    st.markdown("#### 📊 Tổng quan")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_queries = metrics.get("total_queries", 0)
        st.metric("Tổng queries", total_queries)

    with col2:
        agent_mode_pct = metrics.get("agent_mode_percentage", 0)
        st.metric("Agent mode", f"{agent_mode_pct:.1f}%")

    with col3:
        time_saved = metrics.get("total_time_saved", 0)
        st.metric("Time saved", f"{time_saved:.1f}s")

    with col4:
        cache_hit_rate = metrics.get("mcp_cache_hit_rate", "0%")
        st.metric("Cache hit", cache_hit_rate)

    # Detailed metrics
    st.markdown("---")
    st.markdown("#### 🔍 Chi tiết")

    # Mode distribution
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Mode Distribution**")
        agent_count = metrics.get("agent_mode_count", 0)
        direct_count = metrics.get("direct_mode_count", 0)

        if agent_count > 0 or direct_count > 0:
            mode_data = {
                "Agent Mode": agent_count,
                "Direct Mode": direct_count
            }
            st.bar_chart(mode_data)
        else:
            st.caption("Chưa có dữ liệu")

    with col2:
        st.markdown("**MCP Client Stats**")
        cache_hits = metrics.get("mcp_cache_hits", 0)
        cache_misses = metrics.get("mcp_cache_misses", 0)

        if cache_hits > 0 or cache_misses > 0:
            cache_data = {
                "Hits": cache_hits,
                "Misses": cache_misses
            }
            st.bar_chart(cache_data)
        else:
            st.caption("Chưa có dữ liệu")

    # Performance metrics
    st.markdown("---")
    st.markdown("#### ⚡ Performance")

    col1, col2, col3 = st.columns(3)

    with col1:
        avg_routing = metrics.get("avg_routing_time", 0)
        st.metric("Avg routing time", f"{avg_routing:.3f}s")

    with col2:
        avg_response = metrics.get("mcp_avg_response_time", "0s")
        st.metric("Avg MCP response", avg_response)

    with col3:
        failures = metrics.get("mcp_failures", 0)
        st.metric("MCP failures", failures, delta_color="inverse")

    # Router cache stats
    router_cache_hit = metrics.get("router_cache_hit_rate", "0%")
    if router_cache_hit != "0%":
        st.markdown("---")
        st.markdown("#### 🎯 Router Cache")
        st.metric("Router cache hit rate", router_cache_hit)

    # Direct executor stats
    direct_success = metrics.get("direct_success_rate", "0%")
    if direct_success != "0%":
        st.markdown("---")
        st.markdown("#### ⚡ Direct Executor")
        st.metric("Success rate", direct_success)


def render_full_metrics_page(session_manager):
    """
    Render full metrics page (for dedicated metrics page).

    Args:
        session_manager: SessionManager instance
    """

    st.title("📊 System Metrics Dashboard")
    st.caption("Real-time performance metrics của hệ thống Multi-Agent")

    st.markdown("---")

    # Refresh button
    if st.button("🔄 Refresh Metrics", use_container_width=True):
        st.rerun()

    # Render main panel
    render_metrics_panel(session_manager)

    # Additional detailed metrics
    metrics = session_manager.get_metrics()

    if metrics:
        st.markdown("---")
        st.markdown("### 📋 Raw Metrics Data")

        with st.expander("Xem chi tiết JSON", expanded=False):
            st.json(metrics)


def render_metrics_chart(metrics: Dict[str, Any], chart_type: str = "line"):
    """
    Render metrics as chart.

    Args:
        metrics: Metrics dictionary
        chart_type: Type of chart ("line", "bar", "area")
    """

    import pandas as pd

    # Convert metrics to DataFrame format
    data = []

    # Example: Mode distribution over time
    if "agent_mode_count" in metrics and "direct_mode_count" in metrics:
        data.append({
            "Mode": "Agent",
            "Count": metrics["agent_mode_count"]
        })
        data.append({
            "Mode": "Direct",
            "Count": metrics["direct_mode_count"]
        })

    if not data:
        st.info("Không đủ dữ liệu để vẽ biểu đồ")
        return

    df = pd.DataFrame(data)

    if chart_type == "line":
        st.line_chart(df.set_index("Mode"))
    elif chart_type == "bar":
        st.bar_chart(df.set_index("Mode"))
    elif chart_type == "area":
        st.area_chart(df.set_index("Mode"))
