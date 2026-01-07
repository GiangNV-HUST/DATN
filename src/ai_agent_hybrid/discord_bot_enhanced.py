"""
Enhanced Discord Bot with Full Hybrid System Integration

This bot properly implements the architecture from documentation:
- Uses HybridOrchestrator as Root Agent
- Routes to specialized agents (AlertManager, ScreenerSpecialist, etc.)
- Implements chart generation
- Follows sequence diagrams from design doc

Author: Enhanced by AI Assistant
Date: 2026-01-06
"""

import discord
from discord.ext import commands
import asyncio
import logging
import sys
import os
import io
from typing import Optional, Dict
from datetime import datetime
import re

# Fix UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# IMPORTANT: Load .env BEFORE any imports
from dotenv import load_dotenv
final_root = os.path.join(os.path.dirname(__file__), '..', '..')
load_dotenv(os.path.join(final_root, '.env'))

# Add paths
sys.path.insert(0, final_root)
sys.path.insert(0, os.path.dirname(__file__))

# Import Hybrid System components
from hybrid_system.orchestrator import HybridOrchestrator
from hybrid_system.agents.alert_manager import AlertManager
from hybrid_system.agents.subscription_manager import SubscriptionManager
from hybrid_system.agents.screener_specialist import ScreenerSpecialist
from hybrid_system.agents.analysis_specialist import AnalysisSpecialist
from hybrid_system.agents.investment_planner import InvestmentPlanner
from hybrid_system.database import get_database_client

# Chart generation
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EnhancedStockBot(commands.Bot):
    """
    Enhanced Discord Bot với Full Hybrid Architecture

    Architecture (theo tài liệu thiết kế):
    User → Discord Bot → HybridOrchestrator (Root Agent)
                              ↓
                    ┌─────────┴──────────┐
                    │                    │
              Agent Mode          Direct Mode
                    │                    │
          ┌─────────┴─────────┐         │
          │ Specialized Agents │         │
          ├───────────────────┤         │
          │ • AlertManager    │         │
          │ • ScreenerSpec    │         │
          │ • AnalysisSpec    │         │
          │ • InvestmentPlan  │         │
          │ • SubscriptionMgr │         │
          │ • DiscoverySpec   │         │
          └───────────────────┘         │
                    │                    │
                    └─────────┬──────────┘
                              ↓
                         MCP Tools
                              ↓
                          Database

    Features:
    - ✅ Root Agent (HybridOrchestrator)
    - ✅ AI-powered routing
    - ✅ Specialized agents
    - ✅ Chart generation
    - ✅ Dual-mode execution
    - ✅ Transfer mechanism
    """

    def __init__(self):
        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True

        # Initialize bot
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

        # Initialize database client (for charts and direct queries)
        self.db = get_database_client()
        logger.info("✅ Database client initialized")

        # Initialize Hybrid Orchestrator (ROOT AGENT)
        self.orchestrator = None  # Will initialize in async setup_hook

        # Specialized agents (lazy loading)
        self.alert_manager = None
        self.subscription_manager = None
        self.screener_specialist = None
        self.analysis_specialist = None
        self.investment_planner = None

        # Conversation memory
        self.conversations: Dict[int, list] = {}

        # Track active queries
        self.active_queries: set = set()

        # Statistics
        self.stats = {
            "total_queries": 0,
            "agent_mode_count": 0,
            "direct_mode_count": 0,
            "chart_generations": 0,
            "errors": 0,
            "start_time": datetime.now()
        }

        logger.info("✅ Enhanced Stock Bot initialized")

    async def setup_hook(self):
        """Async initialization - called once when bot starts"""
        logger.info("🔄 Initializing Hybrid Orchestrator...")

        # Initialize HybridOrchestrator
        self.orchestrator = HybridOrchestrator()
        await self.orchestrator.initialize()

        logger.info("✅ Hybrid Orchestrator ready (Root Agent active)")

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"🤖 Bot ready! Logged in as {self.user.name}")

        # Set bot presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="@stock_bot <câu hỏi> | Powered by Hybrid AI"
            )
        )

        logger.info(f"📡 Serving {len(self.guilds)} servers")
        logger.info(f"🧠 Root Agent: HybridOrchestrator")
        logger.info(f"🤖 Specialized Agents: 6 agents ready")

    async def on_message(self, message: discord.Message):
        """Handle ALL messages - bot must be mentioned"""
        # Ignore bot's own messages
        if message.author == self.user:
            return

        # Check if bot is mentioned
        if self.user in message.mentions:
            await self.handle_conversation(message)
        # Support ! commands as backup
        elif message.content.startswith("!"):
            await self.process_commands(message)

    async def handle_conversation(self, message: discord.Message):
        """
        Main conversation handler - Routes to Hybrid Orchestrator

        Flow (theo thiết kế):
        1. User gửi tin nhắn
        2. Bot gọi HybridOrchestrator (Root Agent)
        3. Root Agent phân tích và route:
           - Agent Mode → Specialized Agents → MCP Tools
           - Direct Mode → Direct Executor → MCP Tools
        4. Kết quả trả về user
        """
        # Get clean content (remove mention)
        content = message.content
        for mention in message.mentions:
            content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
        content = content.strip()

        if not content:
            await message.channel.send(
                "👋 **Xin chào! Tôi là Stock Bot với AI Hybrid System**\n\n"
                "Bạn có thể hỏi tôi:\n"
                "• 📊 **Giá cổ phiếu**: `@stock_bot giá VCB`\n"
                "• 📈 **Phân tích**: `@stock_bot phân tích HPG chi tiết`\n"
                "• 🔍 **Tìm kiếm**: `@stock_bot tìm cổ phiếu ROE > 15%`\n"
                "• 💼 **Tư vấn**: `@stock_bot với 100 triệu nên đầu tư gì`\n"
                "• 📉 **Biểu đồ**: `@stock_bot vẽ biểu đồ FPT 30 ngày`\n"
                "• 🔔 **Cảnh báo**: `@stock_bot tạo cảnh báo VCB > 90000`\n"
                "• ⭐ **Theo dõi**: `@stock_bot đăng ký theo dõi HPG`\n\n"
                "🤖 **Powered by**: Hybrid AI System với 6 chuyên gia AI"
            )
            return

        # Check for active query
        user_id = str(message.author.id)
        if user_id in self.active_queries:
            await message.channel.send("⏳ Đang xử lý câu hỏi trước của bạn, vui lòng đợi...")
            return

        # Mark as active
        self.active_queries.add(user_id)

        try:
            # Show typing indicator
            async with message.channel.typing():
                # Store in conversation memory
                if user_id not in self.conversations:
                    self.conversations[user_id] = []
                self.conversations[user_id].append({
                    "role": "user",
                    "content": content,
                    "timestamp": datetime.now()
                })
                self.conversations[user_id] = self.conversations[user_id][-5:]

                # ═══════════════════════════════════════════════════════
                # 🎯 MAIN ROUTING LOGIC - HYBRID ORCHESTRATOR (ROOT AGENT)
                # ═══════════════════════════════════════════════════════

                response_parts = []
                routing_info = None

                # Check if query is for chart generation
                if self._is_chart_query(content):
                    # Handle chart separately (custom visual output)
                    chart_result = await self.handle_chart_request(content, message)
                    if chart_result:
                        return  # Chart already sent

                # Process through HybridOrchestrator
                async for event in self.orchestrator.process_query(
                    user_query=content,
                    user_id=user_id,
                    mode="auto"  # Let AI Router decide
                ):
                    if event["type"] == "status":
                        # Status updates
                        logger.info(f"📊 Status: {event['data']}")

                    elif event["type"] == "routing_decision":
                        # Routing decision from AI Router
                        routing_info = event["data"]
                        mode = routing_info["mode"]
                        confidence = routing_info["confidence"]
                        complexity = routing_info["complexity"]

                        logger.info(
                            f"🧠 AI Router Decision: {mode} mode "
                            f"(confidence: {confidence:.2f}, complexity: {complexity:.2f})"
                        )

                        # Update stats
                        if mode == "agent":
                            self.stats["agent_mode_count"] += 1
                        else:
                            self.stats["direct_mode_count"] += 1

                    elif event["type"] == "chunk":
                        # Response chunks
                        response_parts.append(event["data"])

                    elif event["type"] == "error":
                        # Error handling
                        logger.error(f"❌ Error: {event['data']}")
                        response_parts.append(f"\n\n❌ Lỗi: {event['data']}")

                # Combine response
                response = "".join(response_parts)

                # Add routing info footer
                if routing_info:
                    mode_emoji = "🤖" if routing_info["mode"] == "agent" else "⚡"
                    footer = (
                        f"\n\n{mode_emoji} _{routing_info['mode'].title()} Mode_ "
                        f"• Confidence: {routing_info['confidence']:.0%}"
                    )
                    response += footer

                # Update stats
                self.stats["total_queries"] += 1

                # Send response
                if len(response) <= 2000:
                    await message.channel.send(response)
                else:
                    # Split long messages
                    chunks = self.split_message(response, 2000)
                    for chunk in chunks:
                        await message.channel.send(chunk)
                        await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"❌ Error handling conversation: {e}", exc_info=True)
            self.stats["errors"] += 1

            error_msg = "❌ Xin lỗi, đã có lỗi xảy ra khi xử lý câu hỏi của bạn."
            if "quota" in str(e).lower():
                error_msg = "⚠️ API đã vượt quota. Vui lòng thử lại sau."
            elif "timeout" in str(e).lower():
                error_msg = "⏱️ Timeout. Vui lòng thử lại với câu hỏi đơn giản hơn."

            await message.channel.send(error_msg)

        finally:
            # Remove from active queries
            self.active_queries.discard(user_id)

    def _is_chart_query(self, query: str) -> bool:
        """Check if query requests a chart"""
        chart_keywords = ['biểu đồ', 'bieu do', 'chart', 'vẽ', 've', 'graph', 'plot']
        query_lower = query.lower()
        return any(kw in query_lower for kw in chart_keywords)

    async def handle_chart_request(self, query: str, message: discord.Message) -> bool:
        """
        Handle chart generation requests

        Returns:
            bool: True if chart was generated and sent
        """
        try:
            # Extract ticker symbol
            ticker = self.extract_ticker(query)
            if not ticker:
                await message.channel.send(
                    "🤔 Vui lòng chỉ rõ mã cổ phiếu\n"
                    "Ví dụ: `@stock_bot biểu đồ VCB 30 ngày`"
                )
                return False

            # Extract days (default 30)
            days = 30
            days_match = re.search(r'(\d+)\s*(ngày|day|d)', query, re.IGNORECASE)
            if days_match:
                days = int(days_match.group(1))
                days = min(days, 365)  # Cap at 1 year

            # Generate chart
            await message.channel.send(f"📊 Đang tạo biểu đồ {ticker} ({days} ngày)...")

            chart_file = await self.generate_price_chart(ticker, days)

            if chart_file:
                await message.channel.send(
                    f"📈 **Biểu đồ giá {ticker}** ({days} ngày)\n"
                    f"🕒 Dữ liệu mới nhất",
                    file=chart_file
                )
                self.stats["chart_generations"] += 1
                return True
            else:
                await message.channel.send(f"❌ Không thể tạo biểu đồ cho {ticker}")
                return False

        except Exception as e:
            logger.error(f"Error generating chart: {e}", exc_info=True)
            await message.channel.send(f"❌ Lỗi khi tạo biểu đồ: {str(e)}")
            return False

    async def generate_price_chart(self, ticker: str, days: int = 30) -> Optional[discord.File]:
        """
        Generate price chart with technical indicators

        Returns:
            discord.File: Chart image file, or None if failed
        """
        try:
            # Get historical data
            price_data = self.db.get_price_history(ticker, days=days)

            if not price_data or len(price_data) < 2:
                return None

            # Convert to DataFrame for easier plotting
            df = pd.DataFrame(price_data)
            df['time'] = pd.to_datetime(df['time'])
            df = df.sort_values('time')

            # Create figure with 3 subplots
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10),
                                                 gridspec_kw={'height_ratios': [3, 1, 1]})
            fig.suptitle(f'{ticker} - Price Chart ({days} days)', fontsize=16, fontweight='bold')

            # ═══════════════════════════════════════════════════════
            # Subplot 1: Price + Moving Averages
            # ═══════════════════════════════════════════════════════
            ax1.plot(df['time'], df['close'], label='Close Price', color='#2962FF', linewidth=2)

            # MA5 and MA20
            if 'ma5' in df.columns and df['ma5'].notna().any():
                ax1.plot(df['time'], df['ma5'], label='MA5', color='#FF6D00', linewidth=1.5, alpha=0.8)
            if 'ma20' in df.columns and df['ma20'].notna().any():
                ax1.plot(df['time'], df['ma20'], label='MA20', color='#00C853', linewidth=1.5, alpha=0.8)

            ax1.set_ylabel('Price (VND)', fontsize=12, fontweight='bold')
            ax1.legend(loc='upper left', frameon=True, shadow=True)
            ax1.grid(True, alpha=0.3, linestyle='--')
            ax1.set_facecolor('#F5F5F5')

            # ═══════════════════════════════════════════════════════
            # Subplot 2: Volume
            # ═══════════════════════════════════════════════════════
            colors = ['#26A69A' if close >= open_price else '#EF5350'
                      for close, open_price in zip(df['close'], df.get('open', df['close']))]
            ax2.bar(df['time'], df['volume'], color=colors, alpha=0.6, width=0.8)
            ax2.set_ylabel('Volume', fontsize=12, fontweight='bold')
            ax2.grid(True, alpha=0.3, linestyle='--')
            ax2.set_facecolor('#F5F5F5')

            # ═══════════════════════════════════════════════════════
            # Subplot 3: RSI
            # ═══════════════════════════════════════════════════════
            if 'rsi' in df.columns and df['rsi'].notna().any():
                ax3.plot(df['time'], df['rsi'], label='RSI', color='#7C4DFF', linewidth=2)
                ax3.axhline(y=70, color='#EF5350', linestyle='--', linewidth=1, alpha=0.7, label='Overbought (70)')
                ax3.axhline(y=30, color='#26A69A', linestyle='--', linewidth=1, alpha=0.7, label='Oversold (30)')
                ax3.axhline(y=50, color='#757575', linestyle='-', linewidth=0.5, alpha=0.5)
                ax3.set_ylabel('RSI', fontsize=12, fontweight='bold')
                ax3.set_ylim(0, 100)
                ax3.legend(loc='upper left', frameon=True, shadow=True, fontsize=9)
                ax3.grid(True, alpha=0.3, linestyle='--')
                ax3.set_facecolor('#F5F5F5')
            else:
                # If no RSI, remove subplot
                fig.delaxes(ax3)

            # Format x-axis
            date_formatter = DateFormatter('%d/%m')
            for ax in [ax1, ax2, ax3]:
                if ax in fig.axes:
                    ax.xaxis.set_major_formatter(date_formatter)
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

            ax2.set_xlabel('Date', fontsize=12, fontweight='bold')

            # Tight layout
            plt.tight_layout()

            # Save to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
            buf.seek(0)
            plt.close(fig)

            return discord.File(buf, filename=f'{ticker}_chart.png')

        except Exception as e:
            logger.error(f"Error generating chart for {ticker}: {e}", exc_info=True)
            return None

    def extract_ticker(self, query: str) -> Optional[str]:
        """Extract stock ticker from query"""
        # Common Vietnamese stock tickers (3-4 uppercase letters)
        ticker_pattern = r'\b([A-Z]{3,4})\b'
        matches = re.findall(ticker_pattern, query.upper())

        # Filter out common words
        excluded = {'VND', 'RSI', 'MACD', 'USD', 'TCB', 'API'}
        for match in matches:
            if match not in excluded:
                return match
        return None

    def split_message(self, text: str, max_length: int = 2000) -> list:
        """Split long message into chunks"""
        if len(text) <= max_length:
            return [text]

        chunks = []
        current_chunk = ""

        for line in text.split('\n'):
            if len(current_chunk) + len(line) + 1 <= max_length:
                current_chunk += line + '\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line + '\n'

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    @commands.command(name='stats')
    async def show_stats(self, ctx):
        """Show bot statistics"""
        uptime = datetime.now() - self.stats["start_time"]

        embed = discord.Embed(
            title="📊 Bot Statistics",
            color=discord.Color.blue()
        )

        embed.add_field(name="Total Queries", value=self.stats["total_queries"], inline=True)
        embed.add_field(name="Agent Mode", value=self.stats["agent_mode_count"], inline=True)
        embed.add_field(name="Direct Mode", value=self.stats["direct_mode_count"], inline=True)
        embed.add_field(name="Charts Generated", value=self.stats["chart_generations"], inline=True)
        embed.add_field(name="Errors", value=self.stats["errors"], inline=True)
        embed.add_field(name="Uptime", value=str(uptime).split('.')[0], inline=True)

        await ctx.send(embed=embed)


async def main():
    """Main entry point"""
    bot = EnhancedStockBot()

    # Get Discord token
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("❌ DISCORD_BOT_TOKEN not found in .env")
        return

    logger.info("🚀 Starting Enhanced Stock Bot with Hybrid Architecture...")
    logger.info("🧠 Root Agent: HybridOrchestrator")
    logger.info("🤖 Specialized Agents: 6 agents")
    logger.info("📊 Chart Generation: Enabled")

    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
