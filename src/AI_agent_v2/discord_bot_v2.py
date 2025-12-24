"""
Discord Bot V2 - With Function Calling Agent
Bot sử dụng StockAnalysisAgentV2 với Gemini Function Calling
"""

import discord
from discord.ext import commands
import asyncio
import logging
import sys
import os

# Import các module từ project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config import Config
from src.AI_agent_v2.stock_agent_v2 import StockAnalysisAgentV2

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StockBotV2(commands.Bot):
    """Discord Bot V2 với AI Agent Function Calling"""

    def __init__(self):
        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True

        # Khởi tạo bot
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

        # Khởi tạo AI Agent V2
        self.stock_agent = StockAnalysisAgentV2()
        logger.info("✅ AI Agent V2 (Function Calling) initialized")

    async def on_ready(self):
        logger.info(f"✅ Bot V2 đã sẵn sàng! Tên: {self.user.name}")

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="📈 AI Agent V2 | !help",
            )
        )

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        await self.process_commands(message)

        if self.user in message.mentions and not message.content.startswith("!"):
            await self.handle_mention(message)

    async def handle_mention(self, message: discord.Message):
        """Xử lý mention - AI tự quyết định tools"""
        content = message.content.replace(f"<@{self.user.id}>", "").strip()

        if not content:
            await message.reply("Bạn cần hỏi gì về cổ phiếu? 🤔\n*Bot V2 - AI tự động gọi tools*")
            return

        async with message.channel.typing():
            try:
                # Gọi AI V2 - AI tự động gọi tools
                response = await asyncio.to_thread(
                    self.stock_agent.answer_question, content
                )

                await self.send_long_message(message.channel, response)

            except Exception as e:
                logger.error(f"Lỗi khi xử lý mention: {e}", exc_info=True)
                error_msg = str(e)
                if "quota" in error_msg.lower() or "429" in error_msg:
                    error_msg = "⚠️ API đã vượt quota. Vui lòng thử lại sau hoặc liên hệ admin."
                await message.reply(f"❌ {error_msg}")

    async def send_long_message(self, target, content, max_length=2000):
        """Gửi tin nhắn dài, tự động chia"""
        if len(content) <= max_length:
            await target.send(content)
        else:
            chunks = [
                content[i : i + max_length] for i in range(0, len(content), max_length)
            ]
            for i, chunk in enumerate(chunks):
                await target.send(chunk if i == 0 else f"\n{chunk}")
                await asyncio.sleep(0.5)


bot = StockBotV2()


@bot.command(name="help")
async def help_command(ctx):
    """Hướng dẫn sử dụng Bot V2"""
    embed = discord.Embed(
        title="📊 Stock Bot V2 - AI Agent with Function Calling",
        description="Bot phân tích cổ phiếu với AI tự động gọi tools",
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="🆕 Điểm mới V2",
        value="AI tự động quyết định tools nào cần gọi!\nBạn chỉ cần hỏi tự nhiên, AI lo phần còn lại.",
        inline=False,
    )

    embed.add_field(
        name="📈 Phân tích cổ phiếu",
        value="`!analysis <ticker>` - AI tự động lấy data và phân tích\nVí dụ: `!analysis VCB`",
        inline=False,
    )

    embed.add_field(
        name="💬 Hỏi đáp tự nhiên",
        value="`!ask <câu hỏi>` - Hỏi gì cũng được, AI tự hiểu\nVí dụ: `!ask So sánh VCB và TCB`",
        inline=False,
    )

    embed.add_field(
        name="🔍 Tìm kiếm cơ hội",
        value="`!find <tiêu chí>` - AI tự tìm cổ phiếu phù hợp\nVí dụ: `!find cổ phiếu quá bán`",
        inline=False,
    )

    embed.add_field(
        name="💡 Mention Bot",
        value="Tag bot và hỏi bất cứ điều gì!\n@Bot So sánh VCB với VNM về RSI?",
        inline=False,
    )

    embed.set_footer(text="V2: AI Agent with Gemini Function Calling")

    await ctx.send(embed=embed)


@bot.command(name="analysis", aliases=["analyze", "phan-tich"])
async def analysis_command(ctx, ticker: str):
    """Phân tích cổ phiếu - AI tự động gọi tools"""
    ticker = ticker.upper()

    async with ctx.typing():
        try:
            # AI V2 tự động gọi get_latest_price, get_predictions, get_history
            analysis = await asyncio.to_thread(bot.stock_agent.analyze_stock, ticker)

            embed = discord.Embed(
                title=f"📊 Phân tích {ticker} (AI Function Calling)",
                description=analysis[:4096],
                color=discord.Color.green(),
            )

            embed.set_footer(text=f"V2 • Yêu cầu bởi {ctx.author.name}")

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Lỗi phân tích {ticker}: {e}", exc_info=True)
            error_msg = str(e)
            if "quota" in error_msg.lower() or "429" in error_msg:
                error_msg = "⚠️ API đã vượt quota. Vui lòng thử lại sau."
            await ctx.send(f"❌ {error_msg}")


@bot.command(name="ask", aliases=["hoi"])
async def ask_command(ctx, *, question: str):
    """Hỏi đáp tự do - AI tự quyết định tools"""
    async with ctx.typing():
        try:
            # AI V2 tự quyết định cần gọi tool gì
            response = await asyncio.to_thread(
                bot.stock_agent.answer_question, question
            )

            full_response = f"{ctx.author.mention}\n{response}"
            await bot.send_long_message(ctx, full_response)

        except Exception as e:
            logger.error(f"Lỗi ask command: {e}", exc_info=True)
            error_msg = str(e)
            if "quota" in error_msg.lower() or "429" in error_msg:
                error_msg = "⚠️ API đã vượt quota. Vui lòng thử lại sau."
            await ctx.send(f"❌ {error_msg}")


@bot.command(name="find", aliases=["screener", "tim"])
async def find_command(ctx, *, criteria: str):
    """Tìm cổ phiếu - AI tự hiểu tiêu chí và gọi search_stocks"""
    async with ctx.typing():
        try:
            # AI V2 tự parse criteria và gọi search_stocks
            result = await asyncio.to_thread(
                bot.stock_agent.find_opportunities, criteria
            )

            embed = discord.Embed(
                title=f"🔍 Tìm kiếm: {criteria}",
                description=result[:4096],
                color=discord.Color.gold(),
            )

            embed.set_footer(text="V2: AI tự động tìm kiếm")

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Lỗi find command: {e}", exc_info=True)
            await ctx.send(f"❌ Lỗi: {str(e)}")


@bot.command(name="compare", aliases=["so-sanh"])
async def compare_command(ctx, ticker1: str, ticker2: str):
    """So sánh 2 cổ phiếu - AI tự lấy data cả 2 và so sánh"""
    ticker1 = ticker1.upper()
    ticker2 = ticker2.upper()

    async with ctx.typing():
        try:
            question = f"So sánh {ticker1} và {ticker2} về giá, RSI, xu hướng. Cổ phiếu nào tốt hơn?"

            # AI V2 tự động gọi get_latest_price cho cả 2
            response = await asyncio.to_thread(
                bot.stock_agent.answer_question, question
            )

            embed = discord.Embed(
                title=f"⚖️ So sánh {ticker1} vs {ticker2}",
                description=response[:4096],
                color=discord.Color.purple(),
            )

            embed.set_footer(text="V2: AI tự động lấy và so sánh data")

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Lỗi: {str(e)}")


@bot.event
async def on_command_error(ctx, error):
    """Xử lý lỗi commands"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Thiếu tham số: `{error.param.name}`")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Lệnh không tồn tại. Dùng `!help`")
    else:
        logger.error(f"Lỗi: {error}")
        await ctx.send(f"❌ Lỗi: {str(error)}")


def main():
    """Chạy bot V2"""
    token = Config.DISCORD_BOT_TOKEN

    if not token:
        logger.error("❌ Không tìm thấy DISCORD_BOT_TOKEN")
        return

    try:
        logger.info("🚀 Đang khởi động Bot V2 (Function Calling)...")
        bot.run(token)
    except discord.LoginFailure:
        logger.error("❌ Token không hợp lệ!")
    except Exception as e:
        logger.error(f"❌ Lỗi: {e}")


if __name__ == "__main__":
    main()
