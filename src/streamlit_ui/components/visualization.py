"""
Visualization components for stock data
"""

import streamlit as st
import plotly.graph_objects as go
from typing import List, Dict, Any
import pandas as pd


def render_stock_chart(
    data: List[Dict[str, Any]],
    symbol: str,
    chart_type: str = "candlestick"
):
    """
    Render stock price chart using Plotly.

    Args:
        data: List of OHLCV data points
        symbol: Stock symbol
        chart_type: "candlestick", "line", or "ohlc"
    """

    if not data:
        st.warning("Không có dữ liệu để hiển thị")
        return

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Create figure
    fig = go.Figure()

    if chart_type == "candlestick":
        fig.add_trace(go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=symbol
        ))
    elif chart_type == "line":
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['close'],
            mode='lines',
            name=f"{symbol} Close",
            line=dict(color='blue', width=2)
        ))
    elif chart_type == "ohlc":
        fig.add_trace(go.Ohlc(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=symbol
        ))

    # Update layout
    fig.update_layout(
        title=f"{symbol} Price Chart",
        xaxis_title="Date",
        yaxis_title="Price (VND)",
        height=500,
        template="plotly_white",
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)


def render_prediction_chart(
    historical_data: List[Dict[str, Any]],
    prediction_data: List[Dict[str, Any]],
    symbol: str
):
    """
    Render stock price prediction chart with confidence intervals.

    Args:
        historical_data: Historical OHLCV data
        prediction_data: Prediction data with confidence intervals
        symbol: Stock symbol
    """

    if not historical_data or not prediction_data:
        st.warning("Không có dữ liệu dự đoán")
        return

    # Convert to DataFrames
    hist_df = pd.DataFrame(historical_data)
    pred_df = pd.DataFrame(prediction_data)

    # Create figure
    fig = go.Figure()

    # Historical prices
    fig.add_trace(go.Scatter(
        x=hist_df['date'],
        y=hist_df['close'],
        mode='lines',
        name='Historical',
        line=dict(color='blue', width=2)
    ))

    # Predicted prices
    fig.add_trace(go.Scatter(
        x=pred_df['date'],
        y=pred_df['predicted_price'],
        mode='lines+markers',
        name='Prediction',
        line=dict(color='red', width=2, dash='dash')
    ))

    # Confidence interval (upper)
    fig.add_trace(go.Scatter(
        x=pred_df['date'],
        y=pred_df['confidence_upper'],
        mode='lines',
        name='Upper CI',
        line=dict(color='rgba(255,0,0,0.2)', width=0),
        showlegend=False
    ))

    # Confidence interval (lower)
    fig.add_trace(go.Scatter(
        x=pred_df['date'],
        y=pred_df['confidence_lower'],
        mode='lines',
        name='Lower CI',
        line=dict(color='rgba(255,0,0,0.2)', width=0),
        fill='tonexty',
        fillcolor='rgba(255,0,0,0.1)',
        showlegend=True
    ))

    # Update layout
    fig.update_layout(
        title=f"{symbol} Price Prediction with Confidence Intervals",
        xaxis_title="Date",
        yaxis_title="Price (VND)",
        height=500,
        template="plotly_white",
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)


def render_comparison_chart(
    symbols_data: Dict[str, List[Dict[str, Any]]],
    metric: str = "close"
):
    """
    Render comparison chart for multiple symbols.

    Args:
        symbols_data: Dict mapping symbol -> OHLCV data
        metric: Metric to compare ("close", "volume", "change_percent")
    """

    if not symbols_data:
        st.warning("Không có dữ liệu để so sánh")
        return

    # Create figure
    fig = go.Figure()

    # Add trace for each symbol
    for symbol, data in symbols_data.items():
        if not data:
            continue

        df = pd.DataFrame(data)

        if metric in df.columns:
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df[metric],
                mode='lines',
                name=symbol,
                line=dict(width=2)
            ))

    # Update layout
    metric_labels = {
        "close": "Close Price (VND)",
        "volume": "Volume",
        "change_percent": "Change (%)"
    }

    fig.update_layout(
        title=f"Symbol Comparison - {metric_labels.get(metric, metric)}",
        xaxis_title="Date",
        yaxis_title=metric_labels.get(metric, metric),
        height=500,
        template="plotly_white",
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)


def render_portfolio_allocation_chart(allocation_data: Dict[str, float]):
    """
    Render portfolio allocation pie chart.

    Args:
        allocation_data: Dict mapping symbol -> allocation percentage
    """

    if not allocation_data:
        st.warning("Không có dữ liệu phân bổ")
        return

    # Create pie chart
    fig = go.Figure(data=[go.Pie(
        labels=list(allocation_data.keys()),
        values=list(allocation_data.values()),
        hole=0.3,
        textinfo='label+percent',
        textposition='auto'
    )])

    fig.update_layout(
        title="Portfolio Allocation",
        height=400,
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)


def render_metrics_cards(metrics: Dict[str, Any]):
    """
    Render metrics as cards.

    Args:
        metrics: Dictionary of metrics to display
    """

    if not metrics:
        return

    # Create columns dynamically based on number of metrics
    num_metrics = len(metrics)
    cols = st.columns(min(num_metrics, 4))

    for i, (key, value) in enumerate(metrics.items()):
        with cols[i % 4]:
            # Format value
            if isinstance(value, float):
                if "percent" in key.lower() or "%" in str(value):
                    formatted_value = f"{value:.2f}%"
                else:
                    formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)

            # Format label
            label = key.replace("_", " ").title()

            st.metric(label, formatted_value)
