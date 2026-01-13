"""
Discord Bot for Multi-Agent System

Uses MultiAgentOrchestrator with 6 Specialized Agents:
1. AnalysisSpecialist - Stock analysis
2. ScreenerSpecialist - Stock screening
3. AlertManager - Price alerts
4. InvestmentPlanner - Investment planning
5. DiscoverySpecialist - Stock discovery
6. SubscriptionManager - Subscriptions

Features:
- Intelligent routing to appropriate specialist
- Real-time streaming responses
- Interactive embeds with specialist info
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

from hybrid_system.orchestrator.multi_agent_orchestrator import MultiAgentOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Specialist emoji mapping
SPECIALIST_EMOJI = {
    "AnalysisSpecialist": "📊",
    "ScreenerSpecialist": "🔍",
    "AlertManager": "🔔",
    "InvestmentPlanner": "💰",
    "DiscoverySpecialist": "🔮",
    "SubscriptionManager": "📋",
}


class MultiAgentStockBot(commands.Bot):
    """
    Discord Bot powered by Multi-Agent System

    Features:
    - 6 specialized AI agents for different tasks
    - Intelligent query routing
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
        self.orchestrator = None

        # Conversation memory (user_id -> conversation_id)
        self.user_conversations: Dict[int, str] = {}

        # Track active queries
        self.active_queries: set = set()

        # Bot statistics
        self.stats = {
            "total_queries": 0,
            "specialist_usage": {
                "AnalysisSpecialist": 0,
                "ScreenerSpecialist": 0,
                "AlertManager": 0,
                "InvestmentPlanner": 0,
                "DiscoverySpecialist": 0,
                "SubscriptionManager": 0,
            },
            "errors": 0,
            "start_time": datetime.now()
        }

        logger.info("Multi-Agent Stock Bot initialized")

    async def setup_hook(self):
        """Called when bot is setting up - initialize async components"""
        logger.info("Initializing MultiAgentOrchestrator...")
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
                name="Stock Market | !help | Multi-Agent"
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
                "Xin chao! Toi la bot phan tich chung khoan Multi-Agent. "
                "Co 6 chuyen gia AI san sang ho tro ban. Dung `!help` de xem huong dan."
            )
            return

        # Process as natural query
        await self.process_query(message, content, is_mention=True)

    async def process_query(
        self,
        ctx,
        query: str,
        is_mention: bool = False
    ):
        """
        Process user query with MultiAgentOrchestrator

        Args:
            ctx: Discord context (message or command context)
            query: User's question
            is_mention: Whether this is from @mention
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
                f"discord_multi_{user_id}_{datetime.now().timestamp()}"
            )
            self.user_conversations[ctx.author.id] = conversation_id

            # Send initial response
            if is_mention:
                status_msg = await ctx.reply("Dang phan tich va chuyen den chuyen gia phu hop...")
            else:
                status_msg = await ctx.send("Dang xu ly...")

            # Process with MultiAgentOrchestrator
            full_response = []
            tools_used = []
            specialist_used = None
            method_used = None
            start_time = datetime.now()

            try:
                async for event in self.orchestrator.process_query(
                    user_query=query,
                    user_id=user_id,
                    session_id=conversation_id
                ):
                    event_type = event.get("type", "")

                    if event_type == "routing_decision":
                        specialist_used = event["data"].get("specialist")
                        method_used = event["data"].get("method")

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
                            specialist_used = data.get("specialist_used", specialist_used)
                            method_used = data.get("method_used", method_used)

                    elif event_type == "error":
                        error_msg = event.get("data", {})
                        if isinstance(error_msg, dict):
                            full_response.append(f"Loi: {error_msg.get('error', 'Unknown error')}")
                        else:
                            full_response.append(f"Loi: {error_msg}")

                response = "".join(full_response)

            except Exception as e:
                logger.error(f"Error in orchestrator: {e}")
                response = f"Loi xu ly: {str(e)}"

            # Calculate processing time
            elapsed_time = (datetime.now() - start_time).total_seconds()

            # Update statistics
            self.stats["total_queries"] += 1
            if specialist_used and specialist_used in self.stats["specialist_usage"]:
                self.stats["specialist_usage"][specialist_used] += 1

            # Format response with metadata
            emoji = SPECIALIST_EMOJI.get(specialist_used, "🤖")
            footer = f"\n\n---\n{emoji} **{specialist_used or 'Unknown'}**"
            footer += f" | {elapsed_time:.1f}s"
            if tools_used:
                footer += f" | {', '.join(tools_used[:3])}"

            response_with_footer = response + footer

            # Send response with interactive buttons
            view = QueryResponseView(self, query, user_id, specialist_used)

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

            error_msg = "Loi khi xu ly truy van. Vui long thu lai."
            if "quota" in str(e).lower():
                error_msg = "API quota vuot muc. Vui long thu lai sau."

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

    def __init__(self, bot: MultiAgentStockBot, query: str, user_id: str, specialist: str = None):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.bot = bot
        self.query = query
        self.user_id = user_id
        self.specialist = specialist

        # Add buttons
        self.add_item(RefreshButton())
        self.add_item(DetailsButton())
        self.add_item(SpecialistInfoButton(specialist))


class RefreshButton(Button):
    """Button to refresh the query"""

    def __init__(self):
        super().__init__(
            label="Lam moi",
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
            label="Chi tiet",
            style=discord.ButtonStyle.secondary,
            emoji="📊"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Dung `!analysis <ticker>` de xem phan tich chi tiet.",
            ephemeral=True
        )


class SpecialistInfoButton(Button):
    """Button to show specialist info"""

    def __init__(self, specialist: str = None):
        super().__init__(
            label="Chuyen gia",
            style=discord.ButtonStyle.success,
            emoji="🤖"
        )
        self.specialist = specialist

    async def callback(self, interaction: discord.Interaction):
        info = self._get_specialist_info()
        await interaction.response.send_message(
            info,
            ephemeral=True
        )

    def _get_specialist_info(self) -> str:
        specialists_info = {
            "AnalysisSpecialist": "**AnalysisSpecialist** - Phan tich co phieu (gia, ky thuat, co ban, tin tuc)",
            "ScreenerSpecialist": "**ScreenerSpecialist** - Sang loc co phieu theo tieu chi (P/E, ROE, thanh khoan...)",
            "AlertManager": "**AlertManager** - Quan ly canh bao gia",
            "InvestmentPlanner": "**InvestmentPlanner** - Lap ke hoach dau tu, phan bo danh muc",
            "DiscoverySpecialist": "**DiscoverySpecialist** - Tim kiem co phieu tiem nang",
            "SubscriptionManager": "**SubscriptionManager** - Quan ly goi dang ky",
        }
        if self.specialist and self.specialist in specialists_info:
            return specialists_info[self.specialist]
        return "6 chuyen gia AI san sang ho tro ban!"


# Create bot instance
bot = MultiAgentStockBot()


# ============================================================================
# COMMANDS
# ============================================================================

@bot.command(name="help", aliases=["huong-dan"])
async def help_command(ctx):
    """Show help message"""
    embed = discord.Embed(
        title="Multi-Agent Stock Bot - Huong dan",
        description="Bot phan tich chung khoan voi 6 chuyen gia AI",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="**AnalysisSpecialist** - Phan tich",
        value=(
            "`!price <ticker>` - Xem gia hien tai\n"
            "`!analysis <ticker>` - Phan tich chi tiet\n"
            "`!compare <t1> <t2>` - So sanh co phieu"
        ),
        inline=False
    )

    embed.add_field(
        name="**ScreenerSpecialist** - Sang loc",
        value=(
            "`!screener` - Tim co phieu tot\n"
            "`!top` - Top thanh khoan\n"
            "`!bank` - Co phieu ngan hang"
        ),
        inline=False
    )

    embed.add_field(
        name="**InvestmentPlanner** - Tu van",
        value=(
            "`!invest <so von>` - Nhan khuyen nghi dau tu\n"
            "`!dca <ticker> <so tien>` - Ke hoach DCA"
        ),
        inline=False
    )

    embed.add_field(
        name="**DiscoverySpecialist** - Kham pha",
        value=(
            "`!discover` - Tim co phieu tiem nang\n"
            "`!predict <ticker>` - Du doan gia"
        ),
        inline=False
    )

    embed.add_field(
        name="Tro chuyen tu nhien",
        value=(
            "Mention bot: `@bot <cau hoi>`\n"
            "Vi du: `@bot Nen dau tu vao VCB khong?`"
        ),
        inline=False
    )

    embed.add_field(
        name="He thong",
        value=(
            "`!stats` - Thong ke bot\n"
            "`!specialists` - Xem 6 chuyen gia\n"
            "`!ping` - Kiem tra do tre"
        ),
        inline=False
    )

    embed.set_footer(text="6 chuyen gia AI san sang ho tro ban!")

    await ctx.send(embed=embed)


@bot.command(name="ask", aliases=["hoi"])
async def ask_command(ctx, *, question: str):
    """Ask AI any question about stocks"""
    await bot.process_query(ctx, question)


@bot.command(name="price", aliases=["gia"])
async def price_command(ctx, ticker: str):
    """Get current price"""
    ticker = ticker.upper()
    query = f"Cho toi gia co phieu {ticker} hom nay"
    await bot.process_query(ctx, query)


@bot.command(name="analysis", aliases=["phan-tich", "analyze"])
async def analysis_command(ctx, ticker: str):
    """Analyze stock in detail"""
    ticker = ticker.upper()
    query = f"Phan tich ky thuat va co ban co phieu {ticker}"
    await bot.process_query(ctx, query)


@bot.command(name="screener", aliases=["tim", "find"])
async def screener_command(ctx, *, criteria: str = ""):
    """Find stocks by criteria"""
    if criteria:
        query = f"Tim co phieu {criteria}"
    else:
        query = "Top 10 co phieu co thanh khoan cao nhat"
    await bot.process_query(ctx, query)


@bot.command(name="top")
async def top_command(ctx, count: int = 10):
    """Get top stocks by liquidity"""
    query = f"Top {count} co phieu co thanh khoan cao nhat"
    await bot.process_query(ctx, query)


@bot.command(name="bank", aliases=["ngan-hang"])
async def bank_command(ctx):
    """Get banking stocks analysis"""
    query = "Phan tich cac co phieu nganh ngan hang VCB, TCB, MBB, ACB, BID"
    await bot.process_query(ctx, query)


@bot.command(name="invest", aliases=["dau-tu", "recommend"])
async def invest_command(ctx, amount: str = "500000000"):
    """Get investment recommendations"""
    try:
        amount_str = amount.lower().replace(",", "").replace(".", "")
        if "tr" in amount_str or "trieu" in amount_str:
            amount_num = float(amount_str.replace("tr", "").replace("trieu", "").replace("triệu", "")) * 1_000_000
        elif "ty" in amount_str or "tỷ" in amount_str:
            amount_num = float(amount_str.replace("ty", "").replace("tỷ", "")) * 1_000_000_000
        else:
            amount_num = float(amount_str)

        if amount_num >= 1_000_000_000:
            display = f"{amount_num/1_000_000_000:.1f} ty"
        else:
            display = f"{amount_num/1_000_000:.0f} trieu"

        query = f"Toi co {display} muon dau tu co phieu, tu van cho toi"

    except:
        query = f"Toi co 500 trieu muon dau tu co phieu, tu van cho toi"

    await bot.process_query(ctx, query)


@bot.command(name="compare", aliases=["so-sanh"])
async def compare_command(ctx, ticker1: str, ticker2: str):
    """Compare two stocks"""
    ticker1 = ticker1.upper()
    ticker2 = ticker2.upper()
    query = f"So sanh co phieu {ticker1} va {ticker2}, nen mua cai nao?"
    await bot.process_query(ctx, query)


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
        display = f"{monthly_num/1_000_000:.0f} trieu"
    except:
        display = "10 trieu"

    query = f"Tao ke hoach DCA cho co phieu {ticker} voi {display}/thang trong 12 thang"
    await bot.process_query(ctx, query)


@bot.command(name="discover", aliases=["kham-pha"])
async def discover_command(ctx, *, sector: str = ""):
    """Discover potential stocks"""
    if sector:
        query = f"Tim co phieu tiem nang trong nganh {sector}"
    else:
        query = "Tim co phieu tiem nang dang duoc khuyen nghi"
    await bot.process_query(ctx, query)


@bot.command(name="predict", aliases=["du-doan"])
async def predict_command(ctx, ticker: str):
    """Predict stock price for 3 days"""
    ticker = ticker.upper()
    query = f"Du doan gia co phieu {ticker} trong 3 ngay toi"
    await bot.process_query(ctx, query)


@bot.command(name="specialists", aliases=["chuyen-gia"])
async def specialists_command(ctx):
    """Show all 6 specialists"""
    embed = discord.Embed(
        title="6 Chuyen gia AI",
        description="Multi-Agent System voi 6 chuyen gia chuyen biet",
        color=discord.Color.green()
    )

    specialists = [
        ("AnalysisSpecialist", "Phan tich co phieu (gia, ky thuat, co ban, tin tuc)", "5 tools"),
        ("ScreenerSpecialist", "Sang loc co phieu theo tieu chi", "4 tools"),
        ("AlertManager", "Quan ly canh bao gia", "3 tools"),
        ("InvestmentPlanner", "Lap ke hoach dau tu, DCA, quan ly rui ro", "7 tools"),
        ("DiscoverySpecialist", "Tim kiem co phieu tiem nang", "5 tools"),
        ("SubscriptionManager", "Quan ly goi dang ky", "3 tools"),
    ]

    for name, desc, tools in specialists:
        emoji = SPECIALIST_EMOJI.get(name, "🤖")
        embed.add_field(
            name=f"{emoji} {name}",
            value=f"{desc}\n*{tools}*",
            inline=False
        )

    await ctx.send(embed=embed)


@bot.command(name="stats", aliases=["thong-ke"])
async def stats_command(ctx):
    """Show bot statistics"""
    stats = bot.stats
    uptime = datetime.now() - stats["start_time"]

    embed = discord.Embed(
        title="Thong ke Multi-Agent Bot",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Truy van",
        value=f"Tong: {stats['total_queries']}\nLoi: {stats['errors']}",
        inline=True
    )

    # Specialist usage
    usage_text = "\n".join([
        f"{SPECIALIST_EMOJI.get(k, '🤖')} {k.replace('Specialist', '').replace('Manager', '')}: {v}"
        for k, v in stats["specialist_usage"].items() if v > 0
    ])
    if not usage_text:
        usage_text = "Chua co truy van"

    embed.add_field(
        name="Specialist Usage",
        value=usage_text,
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
    await ctx.send(f"Pong! Do tre: {latency}ms")


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Thieu tham so: `{error.param.name}`\nDung `!help` de xem huong dan.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        logger.error(f"Command error: {error}", exc_info=True)
        await ctx.send(f"Da xay ra loi. Vui long thu lai.")


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
