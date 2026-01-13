"""
Discord Bot for AI Agent Multi-Specialist System

Features:
- Multi-Agent Architecture with 6 Specialized Agents
- Smart query processing with MultiAgentOrchestrator
- Real-time streaming responses
- Interactive embeds with buttons
- User conversation memory
- Performance metrics display

UPGRADED: Now uses MultiAgentOrchestrator with 6 Specialists:
- AnalysisSpecialist
- ScreenerSpecialist
- AlertManager
- InvestmentPlanner
- DiscoverySpecialist
- SubscriptionManager
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

# UPGRADED: Use MultiAgentOrchestrator with 6 Specialists
from hybrid_system.orchestrator.multi_agent_orchestrator import MultiAgentOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HybridStockBot(commands.Bot):
    """
    Discord Bot powered by Multi-Agent System with 6 Specialists

    Features:
    - 6 Specialized AI Agents (Analysis, Screener, Alert, Investment, Discovery, Subscription)
    - Smart routing to appropriate specialist
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

        # Initialize MultiAgentOrchestrator (will be done in setup_hook)
        self.orchestrator: Optional[MultiAgentOrchestrator] = None

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

        logger.info("Multi-Agent Stock Bot initialized")

    async def setup_hook(self):
        """Called when bot is setting up - initialize async components"""
        logger.info("Initializing MultiAgentOrchestrator with 6 Specialists...")
        try:
            self.orchestrator = MultiAgentOrchestrator(use_direct_client=True)
            await self.orchestrator.initialize()
            logger.info(f"MultiAgentOrchestrator initialized with {len(self.orchestrator.specialists)} specialists!")
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise

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
                "Xin chào! Tôi là bot phân tích chứng khoán với AI. "
                "Bạn cần giúp gì? Dùng `!help` để xem hướng dẫn."
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
        Process user query with MultiAgentOrchestrator

        Args:
            ctx: Discord context (message or command context)
            query: User's question
            is_mention: Whether this is from @mention
            mode: Execution mode (auto - routes to appropriate specialist)
        """
        # Get user ID
        user_id = str(ctx.author.id)

        # Check if user already has active query
        if user_id in self.active_queries:
            await ctx.reply("Bạn đang có truy vấn đang xử lý. Vui lòng đợi...")
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
                status_msg = await ctx.reply("⏳ Đang xử lý truy vấn của bạn...")
            else:
                status_msg = await ctx.send("⏳ Đang xử lý...")

            # Process with MultiAgentOrchestrator (6 Specialists)
            full_response = []
            tools_used = []
            specialist_used = None
            start_time = datetime.now()

            try:
                async for event in self.orchestrator.process_query(
                    user_query=query,
                    user_id=user_id,
                    mode=mode,
                    session_id=conversation_id
                ):
                    event_type = event.get("type", "")

                    if event_type == "routing_decision":
                        # Capture which specialist was used
                        specialist_used = event.get("data", {}).get("specialist", "Unknown")

                    elif event_type == "chunk":
                        chunk_data = event.get("data", "")
                        if isinstance(chunk_data, dict):
                            full_response.append(chunk_data.get("response", ""))
                            if "tools_used" in chunk_data:
                                tools_used = chunk_data.get("tools_used", [])
                        else:
                            full_response.append(str(chunk_data))

                    elif event_type == "complete":
                        data = event.get("data", {})
                        if isinstance(data, dict):
                            if "response" in data:
                                full_response = [data.get("response", "")]
                            tools_used = data.get("tools_used", tools_used)

                    elif event_type == "error":
                        error_msg = event.get("data", "Unknown error")
                        full_response.append(f"❌ Lỗi: {error_msg}")

                response = "".join(full_response)

            except Exception as e:
                logger.error(f"Error in orchestrator: {e}")
                response = f"❌ Lỗi xử lý: {str(e)}"

            # Calculate processing time
            elapsed_time = (datetime.now() - start_time).total_seconds()

            # Update statistics
            self.stats["total_queries"] += 1
            if specialist_used:
                self.stats["agent_mode"] += 1
            else:
                self.stats["direct_mode"] += 1

            # Format response with metadata
            footer = f"\n\n---\n⏱️ {elapsed_time:.1f}s"
            if specialist_used:
                footer += f" | 🤖 {specialist_used}"
            if tools_used:
                footer += f" | 🔧 {', '.join(tools_used[:3])}"

            response_with_footer = response + footer

            # Send response with interactive buttons
            view = QueryResponseView(self, query, user_id)

            # Edit status message with result
            if len(response_with_footer) <= 2000:
                await status_msg.edit(content=response_with_footer, view=view)
            else:
                # Split long messages
                await status_msg.edit(content=response[:1900] + "...")
                remaining = response[1900:]
                while remaining:
                    chunk = remaining[:1900]
                    if len(remaining) <= 1900:
                        chunk += footer
                    await ctx.send(chunk)
                    remaining = remaining[1900:]
                # Add view to last message
                await ctx.send("---", view=view)

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            self.stats["errors"] += 1

            error_msg = "❌ Lỗi khi xử lý truy vấn. Vui lòng thử lại."
            if "quota" in str(e).lower():
                error_msg = "❌ API quota vượt mức. Vui lòng thử lại sau."

            await ctx.send(error_msg)

        finally:
            # Remove from active queries
            self.active_queries.discard(user_id)

    async def close(self):
        """Cleanup on shutdown"""
        logger.info("Shutting down bot...")
        if self.orchestrator:
            await self.orchestrator.cleanup()
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
            "Đang cập nhật dữ liệu...",
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
            "Dùng `!analysis <ticker>` để xem phân tích chi tiết.",
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
            "Dùng `!help` để xem đầy đủ các lệnh!",
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
        title="🤖 Multi-Agent Stock Bot - Hướng dẫn",
        description="Bot phân tích chứng khoán với 6 AI Specialists",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="📊 Phân tích cơ bản",
        value=(
            "`!price <ticker>` - Xem giá hiện tại\n"
            "`!analysis <ticker>` - Phân tích chi tiết\n"
            "`!ask <câu hỏi>` - Hỏi AI bất kỳ điều gì"
        ),
        inline=False
    )

    embed.add_field(
        name="🔍 Tìm kiếm & Lọc",
        value=(
            "`!screener` - Tìm cổ phiếu tốt\n"
            "`!top` - Top cổ phiếu thanh khoản\n"
            "`!bank` - Cổ phiếu ngân hàng"
        ),
        inline=False
    )

    embed.add_field(
        name="💡 Tư vấn đầu tư",
        value=(
            "`!invest <số vốn>` - Nhận khuyến nghị đầu tư\n"
            "`!compare <ticker1> <ticker2>` - So sánh cổ phiếu\n"
            "`!dca <ticker> <số tiền/tháng>` - Kế hoạch DCA"
        ),
        inline=False
    )

    embed.add_field(
        name="🔮 Dự đoán",
        value=(
            "`!predict <ticker>` - Dự đoán giá 3 ngày\n"
            "`!predict48 <ticker>` - Dự đoán giá 48 ngày"
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
        name="⚙️ Hệ thống",
        value=(
            "`!stats` - Thống kê bot\n"
            "`!ping` - Kiểm tra độ trễ"
        ),
        inline=False
    )

    embed.add_field(
        name="🤖 6 AI Specialists",
        value=(
            "**AnalysisSpecialist** - Phân tích cổ phiếu\n"
            "**ScreenerSpecialist** - Lọc & sàng lọc\n"
            "**InvestmentPlanner** - Tư vấn đầu tư\n"
            "**DiscoverySpecialist** - Khám phá cổ phiếu tiềm năng\n"
            "**AlertManager** - Quản lý cảnh báo\n"
            "**SubscriptionManager** - Theo dõi danh mục"
        ),
        inline=False
    )

    embed.set_footer(text="💡 Tip: Bạn có thể hỏi bằng tiếng Việt tự nhiên! Bot sẽ tự động chọn Specialist phù hợp.")

    await ctx.send(embed=embed)


@bot.command(name="ask", aliases=["hoi"])
async def ask_command(ctx, *, question: str):
    """Ask AI any question about stocks"""
    await bot.process_query(ctx, question, mode="auto")


@bot.command(name="price", aliases=["gia"])
async def price_command(ctx, ticker: str):
    """Get current price"""
    ticker = ticker.upper()
    query = f"Cho tôi giá cổ phiếu {ticker} hôm nay"
    await bot.process_query(ctx, query, mode="auto")


@bot.command(name="analysis", aliases=["phan-tich", "analyze"])
async def analysis_command(ctx, ticker: str):
    """Analyze stock in detail"""
    ticker = ticker.upper()
    query = f"Phân tích kỹ thuật và cơ bản cổ phiếu {ticker}"
    await bot.process_query(ctx, query, mode="auto")


@bot.command(name="screener", aliases=["tim", "find"])
async def screener_command(ctx, *, criteria: str = ""):
    """Find stocks by criteria"""
    if criteria:
        query = f"Tìm cổ phiếu {criteria}"
    else:
        query = "Top 10 cổ phiếu có thanh khoản cao nhất"
    await bot.process_query(ctx, query, mode="auto")


@bot.command(name="top")
async def top_command(ctx, count: int = 10):
    """Get top stocks by liquidity"""
    query = f"Top {count} cổ phiếu có thanh khoản cao nhất"
    await bot.process_query(ctx, query, mode="auto")


@bot.command(name="bank", aliases=["ngan-hang"])
async def bank_command(ctx):
    """Get banking stocks analysis"""
    query = "Phân tích các cổ phiếu ngành ngân hàng VCB, TCB, MBB, ACB, BID"
    await bot.process_query(ctx, query, mode="auto")


@bot.command(name="invest", aliases=["dau-tu", "recommend"])
async def invest_command(ctx, amount: str = "500000000"):
    """Get investment recommendations"""
    # Parse amount (support "500tr", "1ty", etc.)
    try:
        amount_str = amount.lower().replace(",", "").replace(".", "")
        if "tr" in amount_str or "trieu" in amount_str:
            amount_num = float(amount_str.replace("tr", "").replace("trieu", "").replace("triệu", "")) * 1_000_000
        elif "ty" in amount_str or "tỷ" in amount_str:
            amount_num = float(amount_str.replace("ty", "").replace("tỷ", "")) * 1_000_000_000
        else:
            amount_num = float(amount_str)

        # Format for display
        if amount_num >= 1_000_000_000:
            display = f"{amount_num/1_000_000_000:.1f} tỷ"
        else:
            display = f"{amount_num/1_000_000:.0f} triệu"

        query = f"Tôi có {display} muốn đầu tư cổ phiếu, tư vấn cho tôi"

    except:
        query = f"Tôi có 500 triệu muốn đầu tư cổ phiếu, tư vấn cho tôi"

    await bot.process_query(ctx, query, mode="auto")


@bot.command(name="compare", aliases=["so-sanh"])
async def compare_command(ctx, ticker1: str, ticker2: str):
    """Compare two stocks"""
    ticker1 = ticker1.upper()
    ticker2 = ticker2.upper()
    query = f"So sánh cổ phiếu {ticker1} và {ticker2}, nên mua cái nào?"
    await bot.process_query(ctx, query, mode="auto")


@bot.command(name="dca")
async def dca_command(ctx, ticker: str, monthly: str = "10000000"):
    """Generate DCA plan"""
    ticker = ticker.upper()
    try:
        monthly_str = monthly.lower().replace(",", "").replace(".", "")
        if "tr" in monthly_str or "trieu" in monthly_str:
            monthly_num = float(monthly_str.replace("tr", "").replace("trieu", "").replace("triệu", "")) * 1_000_000
        else:
            monthly_num = float(monthly_str)
        display = f"{monthly_num/1_000_000:.0f} triệu"
    except:
        display = "10 triệu"

    query = f"Tạo kế hoạch DCA cho cổ phiếu {ticker} với {display}/tháng trong 12 tháng"
    await bot.process_query(ctx, query, mode="auto")


@bot.command(name="predict", aliases=["du-doan"])
async def predict_command(ctx, ticker: str):
    """Predict stock price for 3 days"""
    ticker = ticker.upper()
    query = f"Dự đoán giá cổ phiếu {ticker} trong 3 ngày tới"
    await bot.process_query(ctx, query, mode="auto")


@bot.command(name="predict48")
async def predict48_command(ctx, ticker: str):
    """Predict stock price for 48 days"""
    ticker = ticker.upper()
    query = f"Dự đoán giá cổ phiếu {ticker} trong 48 ngày tới"
    await bot.process_query(ctx, query, mode="auto")


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

    await ctx.send(embed=embed)


@bot.command(name="ping")
async def ping_command(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Độ trễ: {latency}ms")


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
        logger.info("Starting Multi-Agent Stock Bot...")
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Invalid Discord token!")
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)


if __name__ == "__main__":
    main()
