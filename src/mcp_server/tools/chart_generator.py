"""
Fast Chart Generator with Template Caching
Tạo biểu đồ nhanh bằng cách sử dụng template có sẵn, chỉ thay đổi data

Features:
1. FastChartGenerator: Matplotlib template caching cho ảnh tĩnh (PNG)
   - Lần đầu: ~1.5s (tạo template)
   - Các lần sau: ~0.3-0.5s (chỉ update data)

2. InteractiveChartGenerator: Plotly HTML charts
   - Xuất file HTML interactive ra thư mục Downloads
   - Có MA5, MA20, Volume, và các chỉ số kỹ thuật
"""
import os
import tempfile
import logging
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import numpy as np

logger = logging.getLogger(__name__)

# HTML Template for Plotly charts - cached once
_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Biểu đồ {symbol} - {days} ngày</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #2d3748;
            margin-bottom: 10px;
            font-size: 2em;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .info {{
            color: #718096;
            margin-bottom: 25px;
        }}
        .price-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 25px;
            color: white;
        }}
        .price-item {{
            text-align: center;
        }}
        .price-label {{
            font-size: 0.85em;
            opacity: 0.9;
        }}
        .price-value {{
            font-size: 1.5em;
            font-weight: bold;
        }}
        .price-unit {{
            font-size: 0.75em;
            opacity: 0.8;
        }}
        .status {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }}
        .status.up {{
            background: #48bb78;
            color: white;
        }}
        .status.down {{
            background: #f56565;
            color: white;
        }}
        .status.neutral {{
            background: #a0aec0;
            color: white;
        }}
        .indicators {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .indicator {{
            background: #f7fafc;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .indicator-label {{
            color: #718096;
            font-size: 0.85em;
        }}
        .indicator-value {{
            font-size: 1.3em;
            font-weight: bold;
            color: #2d3748;
        }}
        .indicator-note {{
            font-size: 0.75em;
            color: #e53e3e;
        }}
        #chart {{
            width: 100%;
            height: 600px;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: #a0aec0;
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 Biểu đồ Cổ phiếu {symbol} - {company_name}</h1>
        <div class="info">Dữ liệu {data_points} phiên giao dịch (trong {days} ngày) | Cập nhật: {update_time}</div>

        <div class="price-info">
            <div class="price-item">
                <div class="price-label">Giá đóng cửa</div>
                <div class="price-value">{close_price}</div>
                <div class="price-unit">x1000 VND</div>
            </div>
            <div class="price-item">
                <div class="price-label">Ngày</div>
                <div class="price-value">{last_date}</div>
            </div>
            <div class="price-item">
                <div class="price-label">Khối lượng</div>
                <div class="price-value">{volume}</div>
                <div class="price-unit">cổ phiếu</div>
            </div>
            <div class="price-item">
                <div class="price-label">Trạng thái</div>
                <div class="status {status_class}">{status_text}</div>
            </div>
        </div>

        <div class="indicators">
            <div class="indicator">
                <div class="indicator-label">MA5 (Trung bình 5 ngày)</div>
                <div class="indicator-value">{ma5}</div>
            </div>
            <div class="indicator">
                <div class="indicator-label">MA20 (Trung bình 20 ngày)</div>
                <div class="indicator-value">{ma20}</div>
            </div>
            <div class="indicator">
                <div class="indicator-label">RSI (Chỉ số sức mạnh)</div>
                <div class="indicator-value">{rsi}</div>
                <div class="indicator-note">{rsi_note}</div>
            </div>
        </div>

        <div id="chart"></div>

        <div class="footer">
            Biểu đồ được tạo bởi Stock Market AI Assistant | {update_time}
        </div>
    </div>

    <script>
        {plotly_script}
    </script>
</body>
</html>"""


class InteractiveChartGenerator:
    """
    Tạo biểu đồ HTML interactive với Plotly
    Xuất file ra thư mục Downloads
    """

    def __init__(self):
        # Lấy thư mục Downloads
        self.downloads_dir = Path.home() / "Downloads"
        if not self.downloads_dir.exists():
            self.downloads_dir = Path.home()

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """Tính các chỉ số kỹ thuật"""
        # MA5, MA20
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        return df

    def _get_status(self, df: pd.DataFrame) -> tuple:
        """Xác định trạng thái xu hướng"""
        if len(df) < 2:
            return "neutral", "TRUNG TÍNH"

        last_close = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        ma5 = df['MA5'].iloc[-1] if 'MA5' in df else None
        ma20 = df['MA20'].iloc[-1] if 'MA20' in df else None

        # Đánh giá xu hướng
        if ma5 and ma20 and last_close > ma5 > ma20:
            return "up", "TĂNG MẠNH"
        elif ma5 and last_close > ma5:
            return "up", "TĂNG"
        elif ma5 and ma20 and last_close < ma5 < ma20:
            return "down", "GIẢM MẠNH"
        elif ma5 and last_close < ma5:
            return "down", "GIẢM"
        else:
            return "neutral", "TRUNG TÍNH"

    def _get_rsi_note(self, rsi: float) -> str:
        """Ghi chú về RSI"""
        if pd.isna(rsi):
            return ""
        if rsi >= 70:
            return "⚠️ Vùng quá mua"
        elif rsi <= 30:
            return "⚠️ Vùng quá bán"
        return ""

    def generate_html_chart(
        self,
        symbol: str,
        data: List[Dict],
        days: int = 30,
        display_days: int = None,
        company_name: str = ""
    ) -> Dict:
        """
        Tạo file HTML chart interactive

        Args:
            symbol: Mã cổ phiếu
            data: Dữ liệu giá (có thể nhiều hơn display_days để tính MA)
            days: Số ngày yêu cầu (để hiển thị trong title)
            display_days: Số phiên giao dịch muốn hiển thị (nếu None, hiển thị tất cả)
            company_name: Tên công ty

        Returns:
            Dict với status và file_path
        """
        try:
            if not data:
                return {"status": "error", "message": "No data provided"}

            # Convert to DataFrame
            df = pd.DataFrame(data)
            df['time'] = pd.to_datetime(df['time'])
            df = df.sort_values('time').reset_index(drop=True)

            # Tính indicators trên toàn bộ data (cần đủ data để tính MA20)
            df = self._calculate_indicators(df)

            # Chỉ lấy N phiên giao dịch gần nhất để hiển thị
            if display_days and len(df) > display_days:
                df = df.tail(display_days).reset_index(drop=True)

            # Lấy thông tin mới nhất
            latest = df.iloc[-1]
            status_class, status_text = self._get_status(df)

            ma5_val = f"{latest['MA5']:.2f}" if pd.notna(latest.get('MA5')) else "N/A"
            ma20_val = f"{latest['MA20']:.2f}" if pd.notna(latest.get('MA20')) else "N/A"
            rsi_val = f"{latest['RSI']:.1f}" if pd.notna(latest.get('RSI')) else "N/A"
            rsi_note = self._get_rsi_note(latest.get('RSI', 0))

            # Tạo Plotly script
            plotly_script = self._create_plotly_script(df, symbol)

            # Format volume
            volume_val = latest['volume']
            if volume_val >= 1_000_000:
                volume_str = f"{volume_val/1_000_000:.1f}M"
            elif volume_val >= 1_000:
                volume_str = f"{volume_val/1_000:.1f}K"
            else:
                volume_str = f"{volume_val:,.0f}"

            # Fill template
            html_content = _HTML_TEMPLATE.format(
                symbol=symbol,
                company_name=company_name or symbol,
                days=days,
                data_points=len(df),
                update_time=datetime.now().strftime("%d/%m/%Y %H:%M"),
                close_price=f"{latest['close']:.2f}",
                last_date=latest['time'].strftime("%d/%m/%Y"),
                volume=volume_str,
                status_class=status_class,
                status_text=status_text,
                ma5=ma5_val,
                ma20=ma20_val,
                rsi=rsi_val,
                rsi_note=rsi_note,
                plotly_script=plotly_script
            )

            # Save to Downloads
            filename = f"{symbol.lower()}_chart_{days}days.html"
            file_path = self.downloads_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"Interactive chart saved to: {file_path}")

            return {
                "status": "success",
                "file_path": str(file_path),
                "symbol": symbol,
                "data_points": len(df),
                "message": f"Chart saved to {file_path}"
            }

        except Exception as e:
            logger.error(f"Error generating HTML chart for {symbol}: {e}")
            return {"status": "error", "message": str(e), "symbol": symbol}

    def _create_plotly_script(self, df: pd.DataFrame, symbol: str) -> str:
        """Tạo JavaScript code cho Plotly chart"""

        # Prepare data arrays
        dates = df['time'].dt.strftime('%Y-%m-%d').tolist()
        opens = df['open'].tolist()
        highs = df['high'].tolist()
        lows = df['low'].tolist()
        closes = df['close'].tolist()
        volumes = df['volume'].tolist()

        ma5 = df['MA5'].fillna('null').tolist()
        ma20 = df['MA20'].fillna('null').tolist()

        # Convert None/NaN to null for JS
        ma5_js = [f"{v:.2f}" if isinstance(v, (int, float)) and v != 'null' else 'null' for v in ma5]
        ma20_js = [f"{v:.2f}" if isinstance(v, (int, float)) and v != 'null' else 'null' for v in ma20]

        # Volume colors
        vol_colors = ['rgba(38, 166, 154, 0.7)' if closes[i] >= opens[i] else 'rgba(239, 83, 80, 0.7)'
                      for i in range(len(df))]

        script = f"""
        var dates = {dates};
        var opens = {opens};
        var highs = {highs};
        var lows = {lows};
        var closes = {closes};
        var volumes = {volumes};
        var ma5 = [{','.join(ma5_js)}];
        var ma20 = [{','.join(ma20_js)}];
        var volColors = {vol_colors};

        var candlestick = {{
            x: dates,
            open: opens,
            high: highs,
            low: lows,
            close: closes,
            type: 'candlestick',
            name: '{symbol}',
            increasing: {{line: {{color: '#26a69a'}}, fillcolor: '#26a69a'}},
            decreasing: {{line: {{color: '#ef5350'}}, fillcolor: '#ef5350'}},
            xaxis: 'x',
            yaxis: 'y'
        }};

        var ma5Trace = {{
            x: dates,
            y: ma5,
            type: 'scatter',
            mode: 'lines',
            name: 'MA5',
            line: {{color: '#ff9800', width: 1.5}},
            xaxis: 'x',
            yaxis: 'y'
        }};

        var ma20Trace = {{
            x: dates,
            y: ma20,
            type: 'scatter',
            mode: 'lines',
            name: 'MA20',
            line: {{color: '#2196f3', width: 1.5}},
            xaxis: 'x',
            yaxis: 'y'
        }};

        var volumeTrace = {{
            x: dates,
            y: volumes,
            type: 'bar',
            name: 'Khối lượng',
            marker: {{color: volColors}},
            xaxis: 'x',
            yaxis: 'y2'
        }};

        var layout = {{
            title: {{
                text: 'Biểu đồ giá {symbol} - {len(df)} phiên giao dịch',
                font: {{size: 16}}
            }},
            showlegend: true,
            legend: {{
                orientation: 'h',
                y: 1.02,
                x: 0.5,
                xanchor: 'center'
            }},
            xaxis: {{
                rangeslider: {{visible: false}},
                type: 'category'
            }},
            yaxis: {{
                title: 'Giá (x1000 VND)',
                domain: [0.3, 1],
                autorange: true
            }},
            yaxis2: {{
                title: 'Khối lượng',
                domain: [0, 0.25],
                autorange: true
            }},
            margin: {{t: 50, b: 50, l: 60, r: 30}},
            hovermode: 'x unified'
        }};

        var config = {{
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['lasso2d', 'select2d']
        }};

        Plotly.newPlot('chart', [candlestick, ma5Trace, ma20Trace, volumeTrace], layout, config);
        """

        return script


# Singleton instance for interactive charts
_interactive_generator: Optional[InteractiveChartGenerator] = None


def get_interactive_generator() -> InteractiveChartGenerator:
    """Get singleton interactive chart generator"""
    global _interactive_generator
    if _interactive_generator is None:
        _interactive_generator = InteractiveChartGenerator()
    return _interactive_generator


async def generate_interactive_chart(
    symbol: str,
    data: List[Dict],
    days: int = 30,
    display_days: int = None,
    company_name: str = ""
) -> Dict:
    """
    Async wrapper for interactive HTML chart generation

    Args:
        symbol: Stock symbol
        data: Price data list (may contain extra data for MA calculation)
        days: Number of days requested (for title display)
        display_days: Number of trading sessions to display (if None, show all)
        company_name: Company name for title

    Returns:
        Dict with status and file_path
    """
    import asyncio

    def _sync_generate():
        generator = get_interactive_generator()
        return generator.generate_html_chart(symbol, data, days, display_days, company_name)

    return await asyncio.to_thread(_sync_generate)


class FastChartGenerator:
    """
    Chart Generator với template caching
    - Tạo figure/axes một lần
    - Chỉ update data khi cần vẽ chart mới
    """

    _instance = None
    _fig = None
    _axes = None
    _initialized = False

    def __new__(cls):
        """Singleton pattern - chỉ tạo 1 instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Khởi tạo template nếu chưa có"""
        if not FastChartGenerator._initialized:
            self._setup_template()
            FastChartGenerator._initialized = True

    def _setup_template(self):
        """Tạo figure và axes template một lần"""
        logger.info("Setting up chart template...")

        # Tạo figure với 2 subplots (price + volume)
        FastChartGenerator._fig, FastChartGenerator._axes = plt.subplots(
            2, 1,
            figsize=(12, 8),
            gridspec_kw={'height_ratios': [3, 1]},
            sharex=True
        )

        # Style settings
        FastChartGenerator._fig.set_facecolor('white')
        for ax in FastChartGenerator._axes:
            ax.set_facecolor('white')
            ax.grid(True, linestyle='-', alpha=0.3)
            ax.tick_params(axis='both', labelsize=9)

        # Tight layout
        FastChartGenerator._fig.tight_layout()

        logger.info("Chart template ready!")

    def generate_candlestick(
        self,
        symbol: str,
        data: List[Dict],
        title: Optional[str] = None
    ) -> Dict:
        """
        Vẽ candlestick chart nhanh bằng cách update data vào template

        Args:
            symbol: Mã cổ phiếu
            data: List các dict với keys: time, open, high, low, close, volume

        Returns:
            Dict với status và chart_path
        """
        try:
            if not data:
                return {"status": "error", "message": "No data provided"}

            # Convert to DataFrame
            df = pd.DataFrame(data)
            df['time'] = pd.to_datetime(df['time'])
            df = df.sort_values('time')

            # Clear previous data
            for ax in FastChartGenerator._axes:
                ax.clear()
                ax.grid(True, linestyle='-', alpha=0.3)

            ax_price = FastChartGenerator._axes[0]
            ax_volume = FastChartGenerator._axes[1]

            # Vẽ candlesticks
            width = 0.6
            width2 = 0.1

            # Tính index cho x-axis
            x = np.arange(len(df))

            # Up candles (close > open)
            up = df[df['close'] >= df['open']]
            up_idx = df[df['close'] >= df['open']].index

            # Down candles (close < open)
            down = df[df['close'] < df['open']]
            down_idx = df[df['close'] < df['open']].index

            # Vẽ up candles (xanh)
            if len(up) > 0:
                up_x = [list(df.index).index(i) for i in up_idx]
                ax_price.bar(up_x, up['close'] - up['open'], width, bottom=up['open'],
                           color='#26a69a', edgecolor='#26a69a')
                ax_price.bar(up_x, up['high'] - up['close'], width2, bottom=up['close'],
                           color='#26a69a')
                ax_price.bar(up_x, up['open'] - up['low'], width2, bottom=up['low'],
                           color='#26a69a')

            # Vẽ down candles (đỏ)
            if len(down) > 0:
                down_x = [list(df.index).index(i) for i in down_idx]
                ax_price.bar(down_x, down['close'] - down['open'], width, bottom=down['open'],
                           color='#ef5350', edgecolor='#ef5350')
                ax_price.bar(down_x, down['high'] - down['open'], width2, bottom=down['open'],
                           color='#ef5350')
                ax_price.bar(down_x, down['close'] - down['low'], width2, bottom=down['low'],
                           color='#ef5350')

            # Vẽ volume bars
            colors = ['#26a69a' if df.iloc[i]['close'] >= df.iloc[i]['open'] else '#ef5350'
                     for i in range(len(df))]
            ax_volume.bar(x, df['volume'], width, color=colors, alpha=0.7)

            # X-axis labels (chỉ hiện một số ngày)
            step = max(1, len(df) // 10)
            ax_volume.set_xticks(x[::step])
            ax_volume.set_xticklabels(
                [d.strftime('%d/%m') for d in df['time'].iloc[::step]],
                rotation=45, ha='right'
            )

            # Labels và title
            chart_title = title or f'{symbol} - Candlestick Chart'
            ax_price.set_title(chart_title, fontsize=12, fontweight='bold')
            ax_price.set_ylabel('Price (VND)', fontsize=10)
            ax_volume.set_ylabel('Volume', fontsize=10)
            ax_volume.set_xlabel('Date', fontsize=10)

            # Thêm thông tin giá mới nhất
            latest = df.iloc[-1]
            price_info = f"Close: {latest['close']:,.0f} | Volume: {latest['volume']:,.0f}"
            ax_price.annotate(
                price_info,
                xy=(0.02, 0.98),
                xycoords='axes fraction',
                fontsize=9,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            )

            # Tight layout
            FastChartGenerator._fig.tight_layout()

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name

            FastChartGenerator._fig.savefig(tmp_path, dpi=150, bbox_inches='tight',
                                           facecolor='white', edgecolor='none')

            logger.info(f"Chart generated for {symbol} at {tmp_path}")

            return {
                "status": "success",
                "chart_path": tmp_path,
                "symbol": symbol,
                "data_points": len(df)
            }

        except Exception as e:
            logger.error(f"Error generating chart for {symbol}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "symbol": symbol
            }

    def generate_line_chart(
        self,
        symbol: str,
        data: List[Dict],
        price_column: str = 'close',
        title: Optional[str] = None
    ) -> Dict:
        """
        Vẽ line chart đơn giản (nhanh hơn candlestick)

        Args:
            symbol: Mã cổ phiếu
            data: List các dict
            price_column: Cột giá để vẽ (default: 'close')

        Returns:
            Dict với status và chart_path
        """
        try:
            if not data:
                return {"status": "error", "message": "No data provided"}

            df = pd.DataFrame(data)
            df['time'] = pd.to_datetime(df['time'])
            df = df.sort_values('time')

            # Clear axes
            for ax in FastChartGenerator._axes:
                ax.clear()
                ax.grid(True, linestyle='-', alpha=0.3)

            ax_price = FastChartGenerator._axes[0]
            ax_volume = FastChartGenerator._axes[1]

            # Vẽ line chart
            ax_price.plot(df['time'], df[price_column], color='#1976d2', linewidth=1.5)
            ax_price.fill_between(df['time'], df[price_column], alpha=0.1, color='#1976d2')

            # Volume bars
            colors = ['#26a69a' if df.iloc[i]['close'] >= df.iloc[i]['open'] else '#ef5350'
                     for i in range(len(df))]
            ax_volume.bar(df['time'], df['volume'], width=0.8, color=colors, alpha=0.7)

            # Format x-axis
            ax_volume.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            ax_volume.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(df)//10)))
            plt.setp(ax_volume.xaxis.get_majorticklabels(), rotation=45, ha='right')

            # Labels
            chart_title = title or f'{symbol} - Price Chart'
            ax_price.set_title(chart_title, fontsize=12, fontweight='bold')
            ax_price.set_ylabel('Price (VND)', fontsize=10)
            ax_volume.set_ylabel('Volume', fontsize=10)

            FastChartGenerator._fig.tight_layout()

            # Save
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name

            FastChartGenerator._fig.savefig(tmp_path, dpi=150, bbox_inches='tight')

            return {
                "status": "success",
                "chart_path": tmp_path,
                "symbol": symbol,
                "data_points": len(df)
            }

        except Exception as e:
            logger.error(f"Error generating line chart for {symbol}: {e}")
            return {"status": "error", "message": str(e), "symbol": symbol}


# Singleton instance
_chart_generator: Optional[FastChartGenerator] = None


def get_chart_generator() -> FastChartGenerator:
    """Get singleton chart generator instance"""
    global _chart_generator
    if _chart_generator is None:
        _chart_generator = FastChartGenerator()
    return _chart_generator


async def generate_fast_chart(
    symbol: str,
    data: List[Dict],
    chart_type: str = "candlestick",
    title: Optional[str] = None
) -> Dict:
    """
    Async wrapper for fast chart generation

    Args:
        symbol: Stock symbol
        data: Price data list
        chart_type: "candlestick" or "line"
        title: Optional chart title

    Returns:
        Dict with status and chart_path
    """
    import asyncio

    def _sync_generate():
        generator = get_chart_generator()
        if chart_type == "line":
            return generator.generate_line_chart(symbol, data, title=title)
        return generator.generate_candlestick(symbol, data, title=title)

    return await asyncio.to_thread(_sync_generate)
