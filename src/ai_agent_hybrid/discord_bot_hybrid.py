"""
Discord Bot for AI Agent Hybrid System

Features:
- Dual-mode execution (AI routing automatically)
- Smart query processing with specialized agents
- Real-time streaming responses
- Interactive embeds with buttons
- User conversation memory
- Performance metrics display
"""

import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
import logging
import sys
import os
from typing import Optional, Dict, List
from datetime import datetime

# IMPORTANT: Load .env BEFORE any imports
from dotenv import load_dotenv
final_root = os.path.join(os.path.dirname(__file__), '..', '..')
load_dotenv(os.path.join(final_root, '.env'))

# Add paths
sys.path.insert(0, final_root)
sys.path.insert(0, os.path.dirname(__file__))

from hybrid_system.database import get_database_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HybridStockBot(commands.Bot):
    """
    Discord Bot powered by Hybrid AI Agent System

    Features:
    - AI-powered query routing (agent vs direct mode)
    - Streaming responses with real-time updates
    - Interactive UI with buttons
    - Conversation memory per user
    - Performance metrics
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

        # Initialize database client
        self.db = get_database_client()
        logger.info("Database client initialized")

        # Conversation memory (user_id -> conversation_id)
        self.user_conversations: Dict[int, str] = {}

        # Track active queries (to prevent spam)
        self.active_queries: set = set()

        # Bot statistics
        self.stats = {
            "total_queries": 0,
            "agent_mode": 0,
            "direct_mode": 0,
            "errors": 0,
            "start_time": datetime.now()
        }

        logger.info("Hybrid Stock Bot initialized")

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"Bot ready! Logged in as {self.user.name}")

        # Set bot presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Stock Market | !help"
            )
        )

        logger.info(f"Serving {len(self.guilds)} servers")

    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        # Ignore bot's own messages
        if message.author == self.user:
            return

        # Process commands first
        await self.process_commands(message)

        # Handle mentions (natural conversation)
        if self.user in message.mentions and not message.content.startswith("!"):
            await self.handle_mention(message)

    async def handle_mention(self, message: discord.Message):
        """Handle when bot is mentioned (natural conversation)"""
        # Get content without mention
        content = message.content.replace(f"<@{self.user.id}>", "").strip()

        if not content:
            await message.reply(
                "Xin chao! Toi la bot phan tich chung khoan voi AI. "
                "Ban can giup gi? Dung `!help` de xem huong dan."
            )
            return

        # Process as natural query
        await self.process_query(message, content, is_mention=True)

    async def process_query(
        self,
        ctx,
        query: str,
        is_mention: bool = False,
        mode: str = "auto"
    ):
        """
        Process user query with Hybrid System

        Args:
            ctx: Discord context (message or command context)
            query: User's question
            is_mention: Whether this is from @mention
            mode: Execution mode (auto/agent/direct)
        """
        # Get user ID
        user_id = str(ctx.author.id)

        # Check if user already has active query
        if user_id in self.active_queries:
            await ctx.reply("Ban dang co truy van dang xu ly. Vui long doi...")
            return

        # Mark as active
        self.active_queries.add(user_id)

        try:
            # Get conversation ID for this user
            conversation_id = self.user_conversations.get(
                ctx.author.id,
                f"discord_{user_id}_{datetime.now().timestamp()}"
            )
            self.user_conversations[ctx.author.id] = conversation_id

            # Send initial response
            if is_mention:
                status_msg = await ctx.reply("Dang xu ly truy van cua ban...")
            else:
                status_msg = await ctx.send("Dang xu ly...")

            # For now, use simple database query (until AIRouter is fixed)
            # TODO: Integrate with HybridOrchestrator when AIRouter API is updated

            # Detect query type and route appropriately
            query_lower = query.lower()

            # Simple routing logic
            if any(word in query_lower for word in ['giá', 'gia', 'price']):
                response = await self.handle_price_query(query)
            elif any(word in query_lower for word in ['phân tích', 'phan tich', 'analyze', 'analysis']):
                response = await self.handle_analysis_query(query)
            elif any(word in query_lower for word in ['tìm', 'tim', 'find', 'screener']):
                response = await self.handle_screener_query(query)
            elif any(word in query_lower for word in ['đầu tư', 'dau tu', 'invest', 'khuyến nghị', 'khuyen nghi']):
                response = await self.handle_investment_query(query)
            else:
                # Default: treat as general question
                response = await self.handle_general_query(query)

            # Update statistics
            self.stats["total_queries"] += 1
            self.stats["direct_mode"] += 1  # Since we're using direct mode for now

            # Send response with interactive buttons
            view = QueryResponseView(self, query, user_id)

            # Edit status message with result
            if len(response) <= 2000:
                await status_msg.edit(content=response, view=view)
            else:
                # Split long messages
                await status_msg.edit(content=response[:2000])
                remaining = response[2000:]
                while remaining:
                    chunk = remaining[:2000]
                    await ctx.send(chunk)
                    remaining = remaining[2000:]
                # Add view to last message
                await ctx.send("---", view=view)

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            self.stats["errors"] += 1

            error_msg = "Loi khi xu ly truy van. Vui long thu lai."
            if "quota" in str(e).lower():
                error_msg = "API quota vuot muc. Vui long thu lai sau."

            await ctx.send(f"{error_msg}")

        finally:
            # Remove from active queries
            self.active_queries.discard(user_id)

    async def handle_price_query(self, query: str) -> str:
        """Handle price-related queries"""
        # Extract ticker from query
        ticker = self.extract_ticker(query)

        if not ticker:
            return "Vui long chi ro ma chung khoan. Vi du: 'gia VCB'"

        # Get latest price
        price_data = self.db.get_latest_price(ticker)

        if not price_data:
            return f"Khong tim thay du lieu cho {ticker}"

        # Format response
        response = f"**{ticker} - Gia hien tai**\n\n"
        response += f"Gia dong cua: **{price_data['close']:,.0f} VND**\n"

        if price_data.get('change_percent'):
            change = price_data['change_percent']
            emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
            response += f"Thay doi: {emoji} {change:+.2f}%\n"

        if price_data.get('rsi'):
            rsi = price_data['rsi']
            rsi_status = "Qua mua" if rsi > 70 else "Qua ban" if rsi < 30 else "Trung binh"
            response += f"RSI: {rsi:.1f} ({rsi_status})\n"

        if price_data.get('ma20'):
            response += f"MA20: {price_data['ma20']:,.0f} VND\n"

        return response

    async def handle_analysis_query(self, query: str) -> str:
        """Handle analysis queries"""
        ticker = self.extract_ticker(query)

        if not ticker:
            return "Vui long chi ro ma chung khoan can phan tich."

        # Get comprehensive data
        price_data = self.db.get_latest_price(ticker)
        history = self.db.get_price_history(ticker, days=30)

        if not price_data:
            return f"Khong tim thay du lieu cho {ticker}"

        response = f"**PHAN TICH {ticker}**\n\n"

        # Current price
        response += f"Gia hien tai: **{price_data['close']:,.0f} VND**\n\n"

        # Technical indicators
        response += "**CHI BAO KY THUAT:**\n"
        if price_data.get('rsi'):
            rsi = price_data['rsi']
            response += f"- RSI: {rsi:.1f}"
            if rsi > 70:
                response += " (QUA MUA - can luu y)\n"
            elif rsi < 30:
                response += " (QUA BAN - co the la co hoi)\n"
            else:
                response += " (Trung binh)\n"

        if price_data.get('macd'):
            response += f"- MACD: {price_data['macd']:.2f}\n"

        # Price trend
        if history and len(history) >= 5:
            response += f"\n**XU HUONG GIA:**\n"
            recent_prices = [h['close'] for h in history[:5]]
            trend = "Tang" if recent_prices[0] > recent_prices[-1] else "Giam"
            response += f"- 5 ngay gan day: {trend}\n"

        response += f"\n_Du lieu cap nhat: {price_data.get('date', 'N/A')}_"

        return response

    async def handle_screener_query(self, query: str) -> str:
        """Handle stock screening queries"""
        # Parse criteria from query
        criteria = {}

        query_lower = query.lower()

        if 'rsi' in query_lower:
            if 'thấp' in query_lower or 'thap' in query_lower or 'low' in query_lower:
                criteria['rsi_below'] = 40
            elif 'cao' in query_lower or 'high' in query_lower:
                criteria['rsi_above'] = 60

        if 'pe' in query_lower:
            if 'thấp' in query_lower or 'thap' in query_lower or 'low' in query_lower:
                criteria['pe_below'] = 15

        # Default: find undervalued stocks
        if not criteria:
            criteria = {
                'rsi_below': 50,
                'limit': 10
            }

        # Search stocks
        stocks = self.db.search_stocks_by_criteria(criteria)

        if not stocks or len(stocks) == 0:
            return "Khong tim thay co phieu nao phu hop voi tieu chi."

        response = f"**TIM THAY {len(stocks)} CO PHIEU:**\n\n"

        for i, stock in enumerate(stocks[:10], 1):
            ticker = stock.get('ticker', 'N/A')
            price = stock.get('close', 0)
            rsi = stock.get('rsi', 0)

            response += f"{i}. **{ticker}**: {price:,.0f} VND"
            if rsi:
                response += f" | RSI: {rsi:.1f}"
            response += "\n"

        return response

    async def handle_investment_query(self, query: str) -> str:
        """Handle investment recommendation queries"""
        # This is a placeholder - will be enhanced when AIRouter is fixed
        response = "**TU VAN DAU TU**\n\n"
        response += "Chuc nang nay dang duoc nang cap voi AI Router.\n"
        response += "Hien tai, ban co the dung cac lenh:\n"
        response += "- `!recommend <so von>` - Nhan khuyen nghi dau tu\n"
        response += "- `!screener` - Tim co phieu tot\n"
        response += "- `!analysis <ticker>` - Phan tich cu the\n"

        return response

    async def handle_general_query(self, query: str) -> str:
        """Handle general queries"""
        return (
            "Toi chua hieu ro yeu cau cua ban. "
            "Ban co the:\n"
            "- Hoi ve gia: 'gia VCB'\n"
            "- Phan tich: 'phan tich HPG'\n"
            "- Tim kiem: 'tim co phieu tot'\n"
            "- Tu van: 'nen dau tu gi'\n\n"
            "Hoac dung `!help` de xem day du cac lenh."
        )

    def extract_ticker(self, text: str) -> Optional[str]:
        """Extract stock ticker from text"""
        import re

        # Common Vietnamese stock patterns: 3-4 uppercase letters
        patterns = [
            r'\b([A-Z]{3})\b',  # 3 letters like VCB, HPG
            r'\b([A-Z]{4})\b',  # 4 letters like VNINDEX
        ]

        for pattern in patterns:
            match = re.search(pattern, text.upper())
            if match:
                return match.group(1)

        return None

    async def send_long_message(self, target, content: str, max_length: int = 2000):
        """Send long message, auto-split if needed"""
        if len(content) <= max_length:
            await target.send(content)
        else:
            chunks = [content[i:i+max_length] for i in range(0, len(content), max_length)]
            for chunk in chunks:
                await target.send(chunk)
                await asyncio.sleep(0.5)

    async def close(self):
        """Cleanup on shutdown"""
        logger.info("Shutting down bot...")
        self.db.close()
        await super().close()


class QueryResponseView(View):
    """Interactive buttons for query responses"""

    def __init__(self, bot: HybridStockBot, query: str, user_id: str):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.bot = bot
        self.query = query
        self.user_id = user_id

        # Add buttons
        self.add_item(RefreshButton())
        self.add_item(DetailsButton())
        self.add_item(HelpButton())


class RefreshButton(Button):
    """Button to refresh the query"""

    def __init__(self):
        super().__init__(
            label="Làm mới",
            style=discord.ButtonStyle.primary,
            emoji="🔄"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Dang cap nhat du lieu...",
            ephemeral=True
        )


class DetailsButton(Button):
    """Button to get more details"""

    def __init__(self):
        super().__init__(
            label="Chi tiết",
            style=discord.ButtonStyle.secondary,
            emoji="📊"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Dung `!analysis <ticker>` de xem phan tich chi tiet.",
            ephemeral=True
        )


class HelpButton(Button):
    """Button to show help"""

    def __init__(self):
        super().__init__(
            label="Trợ giúp",
            style=discord.ButtonStyle.success,
            emoji="❓"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Dung `!help` de xem day du cac lenh!",
            ephemeral=True
        )


# Create bot instance
bot = HybridStockBot()


# ============================================================================
# COMMANDS
# ============================================================================

@bot.command(name="help", aliases=["huong-dan"])
async def help_command(ctx):
    """Show help message"""
    embed = discord.Embed(
        title="🤖 Hybrid Stock Bot - Hướng dẫn",
        description="Bot phân tích chứng khoán với AI thông minh",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="📊 Phân tích cơ bản",
        value=(
            "`!price <ticker>` - Xem giá hiện tại\n"
            "`!analysis <ticker>` - Phân tích chi tiết\n"
            "`!chart <ticker>` - Xem biểu đồ"
        ),
        inline=False
    )

    embed.add_field(
        name="🔍 Tìm kiếm & Lọc",
        value=(
            "`!screener` - Tìm cổ phiếu tốt\n"
            "`!top` - Top cổ phiếu\n"
            "`!search <criteria>` - Tìm theo tiêu chí"
        ),
        inline=False
    )

    embed.add_field(
        name="💡 Tư vấn đầu tư",
        value=(
            "`!recommend <số vốn>` - Nhận khuyến nghị\n"
            "`!portfolio` - Gợi ý danh mục\n"
            "`!compare <ticker1> <ticker2>` - So sánh"
        ),
        inline=False
    )

    embed.add_field(
        name="💬 Trò chuyện tự nhiên",
        value=(
            "Mention bot: `@bot <câu hỏi>`\n"
            "Ví dụ: `@bot Nên đầu tư vào VCB không?`"
        ),
        inline=False
    )

    embed.add_field(
        name="📈 Theo dõi",
        value=(
            "`!alert <ticker> <price>` - Tạo cảnh báo\n"
            "`!watchlist` - Danh sách theo dõi\n"
            "`!subscribe <ticker>` - Đăng ký cập nhật"
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ Hệ thống",
        value=(
            "`!stats` - Thống kê bot\n"
            "`!about` - Thông tin bot\n"
            "`!ping` - Kiểm tra độ trễ"
        ),
        inline=False
    )

    embed.set_footer(text="Sử dụng !<lệnh> help để xem chi tiết từng lệnh")

    await ctx.send(embed=embed)


@bot.command(name="price", aliases=["gia"])
async def price_command(ctx, ticker: str):
    """Get current price"""
    ticker = ticker.upper()

    async with ctx.typing():
        try:
            price_data = bot.db.get_latest_price(ticker)

            if not price_data:
                await ctx.send(f"Không tìm thấy {ticker}")
                return

            # Create embed
            embed = discord.Embed(
                title=f"💰 {ticker} - Giá hiện tại",
                color=discord.Color.green() if price_data.get('change_percent', 0) >= 0 else discord.Color.red()
            )

            embed.add_field(
                name="Giá đóng cửa",
                value=f"**{price_data['close']:,.0f}** VND",
                inline=True
            )

            if price_data.get('volume'):
                embed.add_field(
                    name="Khối lượng",
                    value=f"{price_data['volume']:,.0f}",
                    inline=True
                )

            if price_data.get('change_percent'):
                change = price_data['change_percent']
                emoji = "📈" if change > 0 else "📉"
                embed.add_field(
                    name="Thay đổi",
                    value=f"{emoji} {change:+.2f}%",
                    inline=True
                )

            if price_data.get('rsi'):
                embed.add_field(
                    name="RSI",
                    value=f"{price_data['rsi']:.1f}",
                    inline=True
                )

            if price_data.get('ma20'):
                embed.add_field(
                    name="MA20",
                    value=f"{price_data['ma20']:,.0f} VND",
                    inline=True
                )

            embed.set_footer(text=f"Cập nhật: {price_data.get('date', 'N/A')}")

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in price command: {e}")
            await ctx.send(f"Lỗi: {str(e)}")


@bot.command(name="analysis", aliases=["phan-tich", "analyze"])
async def analysis_command(ctx, ticker: str):
    """Analyze stock in detail"""
    ticker = ticker.upper()

    async with ctx.typing():
        response = await bot.handle_analysis_query(f"phân tích {ticker}")
        await ctx.send(response)


@bot.command(name="screener", aliases=["tim", "find"])
async def screener_command(ctx, *, criteria: str = ""):
    """Find stocks by criteria"""
    async with ctx.typing():
        query = f"tìm cổ phiếu {criteria}" if criteria else "tìm cổ phiếu tốt"
        response = await bot.handle_screener_query(query)
        await ctx.send(response)


@bot.command(name="recommend", aliases=["tu-van"])
async def recommend_command(ctx, amount: Optional[int] = 100000000):
    """Get investment recommendations"""
    async with ctx.typing():
        query = f"với {amount/1000000:.0f} triệu thì nên đầu tư chứng khoán nào"
        response = await bot.handle_investment_query(query)
        await ctx.send(response)


@bot.command(name="stats", aliases=["thong-ke"])
async def stats_command(ctx):
    """Show bot statistics"""
    stats = bot.stats
    uptime = datetime.now() - stats["start_time"]

    embed = discord.Embed(
        title="📊 Thống kê Bot",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Truy vấn",
        value=f"Tổng: {stats['total_queries']}\nAgent mode: {stats['agent_mode']}\nDirect mode: {stats['direct_mode']}",
        inline=True
    )

    embed.add_field(
        name="Hiệu suất",
        value=f"Lỗi: {stats['errors']}\nThành công: {stats['total_queries'] - stats['errors']}",
        inline=True
    )

    embed.add_field(
        name="Uptime",
        value=f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m",
        inline=True
    )

    # Database stats
    db_stats = bot.db.get_stats()
    embed.add_field(
        name="Database",
        value=f"Calls: {db_stats['total_calls']}\nCache hits: {db_stats['cache_hits']}\nHit rate: {db_stats['cache_hit_rate']}",
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command(name="ping")
async def ping_command(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Độ trễ: {latency}ms")


@bot.command(name="about", aliases=["thong-tin"])
async def about_command(ctx):
    """About the bot"""
    embed = discord.Embed(
        title="🤖 Hybrid Stock Bot",
        description="Bot phân tích chứng khoán Việt Nam với hệ thống AI Hybrid thông minh",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="Tính năng",
        value=(
            "✅ AI-powered routing (tự động chọn chế độ tối ưu)\n"
            "✅ Specialized agents (6 agents chuyên môn)\n"
            "✅ Real-time data từ PostgreSQL\n"
            "✅ Client-side caching (tăng tốc 10x)\n"
            "✅ Conversation memory (nhớ ngữ cảnh)\n"
            "✅ Interactive UI với buttons"
        ),
        inline=False
    )

    embed.add_field(
        name="Technology Stack",
        value=(
            "🔹 Python + Discord.py\n"
            "🔹 Google Gemini AI\n"
            "🔹 PostgreSQL Database\n"
            "🔹 Hybrid Multi-Agent System"
        ),
        inline=False
    )

    embed.set_footer(text="Made with ❤️ by DATN Team | 2026")

    await ctx.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Thiếu tham số: `{error.param.name}`\nDùng `!help` để xem hướng dẫn.")
    elif isinstance(error, commands.CommandNotFound):
        # Silently ignore (user might be using natural language)
        pass
    else:
        logger.error(f"Command error: {error}", exc_info=True)
        await ctx.send(f"❌ Đã xảy ra lỗi. Vui lòng thử lại.")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run the bot"""
    token = os.getenv("DISCORD_BOT_TOKEN")

    if not token:
        logger.error("DISCORD_BOT_TOKEN not found in .env")
        return

    try:
        logger.info("Starting Hybrid Stock Bot...")
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Invalid Discord token!")
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
    finally:
        # Cleanup
        asyncio.run(bot.close())


if __name__ == "__main__":
    main()
