"""
Discord Bot for Multi-Agent System

Uses MultiAgentOrchestrator with 8 Specialized Agents:
1. AnalysisSpecialist - Stock analysis
2. ScreenerSpecialist - Stock screening
3. AlertManager - Price alerts
4. InvestmentPlanner - Investment planning
5. DiscoverySpecialist - Stock discovery
6. SubscriptionManager - Subscriptions
7. MarketContextSpecialist - Market overview (VN-Index, sectors)
8. ComparisonSpecialist - Stock comparison

Features:
- AI-Powered routing (OpenAI GPT-4o-mini)
- OpenAI post-processing for beautiful responses (like Claude Desktop)
- Multi-agent workflow support (sequential/parallel)
- Natural conversation via @mention
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
from openai import OpenAI

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

# Initialize OpenAI client for post-processing
openai_client = OpenAI()

# Specialist emoji mapping (8 specialists)
SPECIALIST_EMOJI = {
    "AnalysisSpecialist": "📊",
    "ScreenerSpecialist": "🔍",
    "AlertManager": "🔔",
    "InvestmentPlanner": "💰",
    "DiscoverySpecialist": "🔮",
    "SubscriptionManager": "📋",
    "MarketContextSpecialist": "📈",
    "ComparisonSpecialist": "⚖️",
}


# ==================== OPENAI POST-PROCESSING ====================

def format_response_with_openai(user_query: str, raw_response: str, specialist: str, model: str = "gpt-4o-mini") -> str:
    """
    Use OpenAI to format and enhance the raw agent response.
    Similar to how Claude Desktop uses Claude AI to post-process MCP results.

    Args:
        user_query: Original user question
        raw_response: Raw output from specialist agent
        specialist: Name of the specialist that generated the response
        model: OpenAI model to use

    Returns:
        Formatted, user-friendly response
    """
    if not raw_response or len(raw_response.strip()) < 10:
        return raw_response

    system_prompt = """Ban la tro ly AI chuyen ve co phieu Viet Nam. Nhiem vu cua ban la format lai ket qua tu he thong Multi-Agent thanh cau tra loi tu nhien, de hieu cho nguoi dung.

QUY TAC QUAN TRONG:
1. GIU NGUYEN tat ca so lieu, ma co phieu, gia ca - KHONG duoc thay doi bat ky data nao
2. Format thanh markdown de hien thi dep (dung headers, bold, tables, lists)
3. Them phan tich/nhan xet ngan gon neu phu hop
4. Tra loi bang tieng Viet, tu nhien nhu dang noi chuyen
5. Neu data cho thay diem tot/xau, hay highlight ra
6. Neu co nhieu co phieu, co the dung bang de so sanh
7. Ket thuc bang 1-2 cau khuyen nghi hoac luu y neu phu hop
8. KHONG them thong tin khong co trong data goc
9. KHONG noi "Dua tren du lieu" hoac "Theo he thong" - tra loi truc tiep

VERIFY CALCULATIONS (RAT QUAN TRONG):
- Neu la ke hoach DCA: Tong dau tu = So tien moi thang x So thang
  Vi du: 5 trieu/thang x 12 thang = 60 trieu (KHONG PHAI 127 trieu)
- Neu so lieu trong raw_response SAI so voi phep tinh don gian, hay SUA LAI cho dung
- Tinh toan lai neu can thiet va hien thi so lieu DUNG

FORMAT OUTPUT CHO DISCORD:
- Su dung **bold** cho ten co phieu va so lieu quan trong
- Su dung bullet points cho danh sach
- Giu response NGAN GON (duoi 1800 ky tu neu co the) vi Discord gioi han 2000 ky tu
- Khong dung headers ## qua nhieu, chi dung khi can thiet"""

    user_prompt = f"""Cau hoi nguoi dung: "{user_query}"

Ket qua tu {specialist}:
{raw_response}

Hay format lai thanh cau tra loi tu nhien, de hieu, NGAN GON cho Discord.

LUU Y QUAN TRONG:
- Kiem tra lai cac phep tinh (dac biet la DCA: tong dau tu = so tien/thang x so thang)
- Neu so lieu SAI, hay tinh lai va hien thi so DUNG
- Giu nguyen cac so lieu khac neu chinh xac
- Response phai duoi 1800 ky tu"""

    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        # If OpenAI fails, return raw response
        logger.error(f"OpenAI formatting error: {e}")
        return raw_response


class MultiAgentStockBot(commands.Bot):
    """
    Discord Bot powered by Multi-Agent System (8 Specialists)

    Features:
    - 8 specialized AI agents for different tasks
    - AI-powered query routing
    - OpenAI post-processing for beautiful responses
    - Multi-agent workflow support
    - Natural conversation via @mention
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

        # Settings
        self.use_openai_formatting = True
        self.openai_model = "gpt-4o-mini"

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
                "MarketContextSpecialist": 0,
                "ComparisonSpecialist": 0,
            },
            "multi_agent_queries": 0,
            "errors": 0,
            "start_time": datetime.now()
        }

        logger.info("Multi-Agent Stock Bot initialized (8 Specialists)")

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
                name="Stock Market | @mention để hỏi"
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

        # Handle mentions (natural conversation) - PRIMARY WAY TO INTERACT
        if self.user in message.mentions and not message.content.startswith("!"):
            await self.handle_mention(message)

    async def handle_mention(self, message: discord.Message):
        """Handle when bot is mentioned (natural conversation)"""
        # Get content without mention
        content = message.content.replace(f"<@{self.user.id}>", "").strip()

        if not content:
            # Show welcome message with examples
            embed = discord.Embed(
                title="🤖 Xin chào! Tôi là AI Stock Advisor",
                description="Hỏi tôi bất cứ điều gì về cổ phiếu Việt Nam!",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="💡 Ví dụ câu hỏi",
                value=(
                    "• Phân tích cổ phiếu FPT\n"
                    "• So sánh VCB và TCB\n"
                    "• Tổng quan thị trường hôm nay\n"
                    "• Lọc cổ phiếu P/E < 15\n"
                    "• Tư vấn đầu tư 100 triệu\n"
                    "• Lập kế hoạch DCA cho VNM 5 triệu/tháng"
                ),
                inline=False
            )

            embed.add_field(
                name="🎯 8 Chuyên gia AI",
                value=(
                    "📊 Phân tích | 🔍 Sàng lọc | 📈 Thị trường\n"
                    "⚖️ So sánh | 💰 Đầu tư | 🔮 Khám phá\n"
                    "🔔 Cảnh báo | 📋 Đăng ký"
                ),
                inline=False
            )

            embed.set_footer(text="Chỉ cần @mention tôi và đặt câu hỏi!")

            await message.reply(embed=embed)
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
            await ctx.reply("⏳ Bạn đang có truy vấn đang xử lý. Vui lòng đợi...")
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

            # Send initial response with typing indicator
            status_msg = await ctx.reply("🔄 Đang phân tích và chuyển đến chuyên gia phù hợp...")

            # Process with MultiAgentOrchestrator
            full_response = []
            tools_used = []
            specialist_used = None
            method_used = None
            start_time = datetime.now()

            # Multi-agent tracking
            is_multi_agent = False
            execution_mode = "single"
            tasks_info = []
            specialist_responses = {}

            try:
                async for event in self.orchestrator.process_query(
                    user_query=query,
                    user_id=user_id,
                    session_id=conversation_id
                ):
                    event_type = event.get("type", "")

                    if event_type == "routing_decision":
                        data = event.get("data", {})
                        specialist_used = data.get("specialist")
                        method_used = data.get("method")
                        is_multi_agent = data.get("is_multi_agent", False)
                        execution_mode = data.get("execution_mode", "single")
                        tasks_info = data.get("tasks", [])

                        # Update status message for multi-agent
                        if is_multi_agent and tasks_info:
                            specialists_list = [t.get("specialist", "") for t in tasks_info]
                            mode_text = "tuần tự" if execution_mode == "sequential" else "song song"
                            await status_msg.edit(
                                content=f"🔄 **Multi-Agent Workflow** ({mode_text})\n"
                                        f"Đang xử lý với: {' → '.join(specialists_list)}..."
                            )

                    elif event_type == "task_start":
                        # Update status for each task
                        data = event.get("data", {})
                        task_specialist = data.get("specialist", "")
                        task_method = data.get("method", "")
                        emoji = SPECIALIST_EMOJI.get(task_specialist, "🤖")
                        if is_multi_agent:
                            await status_msg.edit(
                                content=f"🔄 {emoji} Đang xử lý: **{task_specialist}**.{task_method}..."
                            )

                    elif event_type == "task_complete":
                        data = event.get("data", {})
                        task_specialist = data.get("specialist", "")
                        task_response = data.get("response", "")
                        if task_specialist:
                            specialist_responses[task_specialist] = task_response

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
                            full_response.append(f"❌ Lỗi: {error_msg.get('error', 'Unknown error')}")
                        else:
                            full_response.append(f"❌ Lỗi: {error_msg}")

                response = "".join(full_response)

            except Exception as e:
                logger.error(f"Error in orchestrator: {e}")
                response = f"❌ Lỗi xử lý: {str(e)}"

            # Calculate processing time
            elapsed_time = (datetime.now() - start_time).total_seconds()

            # Update statistics
            self.stats["total_queries"] += 1
            if is_multi_agent:
                self.stats["multi_agent_queries"] += 1
            if specialist_used and specialist_used in self.stats["specialist_usage"]:
                self.stats["specialist_usage"][specialist_used] += 1

            # Apply OpenAI formatting if enabled
            if self.use_openai_formatting and response and not response.startswith("❌"):
                try:
                    formatted_response = format_response_with_openai(
                        user_query=query,
                        raw_response=response,
                        specialist=specialist_used or "Unknown",
                        model=self.openai_model
                    )
                    response = formatted_response
                except Exception as e:
                    logger.error(f"OpenAI formatting failed: {e}")

            # Build footer with metadata
            emoji = SPECIALIST_EMOJI.get(specialist_used, "🤖")
            footer_parts = [f"{emoji} {specialist_used or 'AI'}"]
            footer_parts.append(f"⏱️ {elapsed_time:.1f}s")

            if is_multi_agent:
                footer_parts.append(f"🔗 Multi-Agent ({execution_mode})")

            if self.use_openai_formatting:
                footer_parts.append("✨ OpenAI")

            footer = "\n\n---\n" + " | ".join(footer_parts)

            response_with_footer = response + footer

            # Send response
            if len(response_with_footer) <= 2000:
                await status_msg.edit(content=response_with_footer)
            else:
                # Split long messages
                await status_msg.edit(content=response[:1900] + "...")
                remaining = response[1900:]
                while remaining:
                    chunk = remaining[:1900]
                    if len(remaining) <= 1900:
                        chunk += footer
                    await ctx.channel.send(chunk)
                    remaining = remaining[1900:]

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            self.stats["errors"] += 1

            error_msg = "❌ Lỗi khi xử lý truy vấn. Vui lòng thử lại."
            if "quota" in str(e).lower():
                error_msg = "⚠️ API quota vượt mức. Vui lòng thử lại sau."

            await ctx.reply(error_msg)

        finally:
            # Remove from active queries
            self.active_queries.discard(user_id)

    async def close(self):
        """Cleanup on shutdown"""
        logger.info("Shutting down bot...")
        if self.orchestrator:
            await self.orchestrator.cleanup()
        await super().close()


# Create bot instance
bot = MultiAgentStockBot()


# ============================================================================
# COMMANDS (Minimal - encourage @mention usage)
# ============================================================================

@bot.command(name="help", aliases=["huong-dan", "h"])
async def help_command(ctx):
    """Show help message"""
    embed = discord.Embed(
        title="🤖 AI Stock Advisor - Hướng dẫn",
        description="**Cách đơn giản nhất:** @mention bot và đặt câu hỏi!",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="💬 Cách sử dụng",
        value=(
            f"**@{bot.user.name if bot.user else 'bot'}** + câu hỏi của bạn\n\n"
            "Ví dụ:\n"
            f"• @bot Phân tích FPT\n"
            f"• @bot So sánh VCB và TCB\n"
            f"• @bot Thị trường hôm nay thế nào?\n"
            f"• @bot Tư vấn đầu tư 500 triệu\n"
            f"• @bot Lập DCA cho VNM 10 triệu/tháng"
        ),
        inline=False
    )

    embed.add_field(
        name="🎯 8 Chuyên gia AI sẵn sàng hỗ trợ",
        value=(
            "📊 **Phân tích** - Phân tích cổ phiếu chi tiết\n"
            "🔍 **Sàng lọc** - Lọc cổ phiếu theo tiêu chí\n"
            "📈 **Thị trường** - Tổng quan VN-Index, ngành\n"
            "⚖️ **So sánh** - So sánh nhiều cổ phiếu\n"
            "💰 **Đầu tư** - Tư vấn, lập kế hoạch DCA\n"
            "🔮 **Khám phá** - Tìm cổ phiếu tiềm năng\n"
            "🔔 **Cảnh báo** - Quản lý cảnh báo giá\n"
            "📋 **Đăng ký** - Quản lý gói dịch vụ"
        ),
        inline=False
    )

    embed.add_field(
        name="⚡ Lệnh nhanh (tùy chọn)",
        value=(
            "`!stats` - Thống kê bot\n"
            "`!ping` - Kiểm tra độ trễ"
        ),
        inline=False
    )

    embed.set_footer(text="Hệ thống Multi-Agent với OpenAI post-processing")

    await ctx.send(embed=embed)


@bot.command(name="stats", aliases=["thong-ke"])
async def stats_command(ctx):
    """Show bot statistics"""
    stats = bot.stats
    uptime = datetime.now() - stats["start_time"]

    embed = discord.Embed(
        title="📊 Thống kê Multi-Agent Bot",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="📈 Truy vấn",
        value=(
            f"Tổng: **{stats['total_queries']}**\n"
            f"Multi-Agent: **{stats['multi_agent_queries']}**\n"
            f"Lỗi: **{stats['errors']}**"
        ),
        inline=True
    )

    # Top specialists
    top_specialists = sorted(
        stats["specialist_usage"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    usage_text = "\n".join([
        f"{SPECIALIST_EMOJI.get(k, '🤖')} {k.replace('Specialist', '').replace('Manager', '')}: **{v}**"
        for k, v in top_specialists if v > 0
    ])
    if not usage_text:
        usage_text = "Chưa có truy vấn"

    embed.add_field(
        name="🎯 Top Specialists",
        value=usage_text,
        inline=True
    )

    embed.add_field(
        name="⏱️ Uptime",
        value=f"**{uptime.days}**d **{uptime.seconds//3600}**h **{(uptime.seconds//60)%60}**m",
        inline=True
    )

    embed.add_field(
        name="⚙️ Settings",
        value=(
            f"OpenAI Format: **{'✅' if bot.use_openai_formatting else '❌'}**\n"
            f"Model: **{bot.openai_model}**"
        ),
        inline=True
    )

    await ctx.send(embed=embed)


@bot.command(name="ping")
async def ping_command(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Độ trễ: **{latency}ms**")


@bot.command(name="ask", aliases=["hoi", "a"])
async def ask_command(ctx, *, question: str):
    """Ask AI any question about stocks (fallback command)"""
    await bot.process_query(ctx, question)


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Thiếu tham số. Hãy @mention bot và đặt câu hỏi trực tiếp!")
    elif isinstance(error, commands.CommandNotFound):
        # Ignore unknown commands - users should use @mention
        pass
    else:
        logger.error(f"Command error: {error}", exc_info=True)
        await ctx.send(f"❌ Đã xảy ra lỗi. Hãy thử @mention bot và đặt câu hỏi.")


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
        logger.info("Starting Multi-Agent Stock Bot (8 Specialists)...")
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Invalid Discord token!")
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)


if __name__ == "__main__":
    main()
