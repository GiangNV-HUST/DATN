import discord
from discord.ext import commands
import asyncio
import logging
import sys
import os

# Import các module từ project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config import Config
from src.AI_agent.stock_agent import StockAnalysisAgent

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StockBot(commands.Bot):
    def __init__(self):
        # Setup intents (quyền của bot)
        intents = discord.Intents.default()
        intents.message_content = True  # Cho phép đọc nội dung của tin nhắn
        intents.messages = True

        # Khởi tạo bot với prefix "!"
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,  # Tắt help mặc định
        )

        # Khởi tạo AI Agent
        self.stock_agent = StockAnalysisAgent()
        logger.info("AI Agent initialized")

    async def on_ready(self):
        logger.info(f"✅ Bot đã sẵn sàng! Tên: {self.user.name}")

        # Set bot status (trạng thái hiện thị)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="📈 Thị trường chứng khoán | !help",
            )
        )

    async def on_message(self, message: discord.Message):
        # Bỏ qua tin nhắn từ chính bot
        if message.author == self.user:
            return

        # Xử lý commands(!analysis, !ask, etc.)
        await self.process_commands(message)

        # Xử lý mention bot (Khi người dùng tag bot)
        if self.user in message.mentions and not message.content.startswith("!"):
            await self.handle_mention(message)

    async def handle_mention(self, message: discord.Message):
        # Lấy nội dung(bỏ mention)
        content = message.content.replace(f"<@{self.user.id}>", "").strip()

        if not content:
            await message.reply("Bạn cần hỏi gì về cổ phiếu? 🤔")
            return

        # Hiện thị "đang gõ..."
        async with message.channel.typing():
            try:
                # Gọi AI để trả lời (Chạy trong thread pool để không block event loop)
                response = await asyncio.to_thread(
                    self.stock_agent.answer_question, content
                )

                # Gửi tin nhắn (tự động chia nếu dài)
                await self.send_long_message(message.channel, response)

            except Exception as e:
                logger.error(f"Lỗi khi xử lý mention: {e}", exc_info=True)
                # Tạo error message dễ hiểu cho user
                error_msg = str(e)
                if "quota" in error_msg.lower() or "429" in error_msg:
                    error_msg = "⚠️ API đã vượt quota. Vui lòng thử lại sau hoặc liên hệ admin."
                await message.reply(f"❌ {error_msg}")

    async def send_long_message(self, target, content, max_length=2000):
        """
        Gửi tin nhắn dài, tự động chia thành nhiều tin nhắn nếu vượt quá giới hạn

        Args:
            target: discord.abc.Messageable(ctx, message, channel, etc.)
            content: Nội dung cần gửi
            max_length: Độ dài tối đa mỗi tin nhắn (mặc định 2000)
        """
        if len(content) <= max_length:
            await target.send(content)
        else:
            # Tin nhắn dài, chia thành nhiều phần
            chunks = [
                content[i : i + max_length] for i in range(0, len(content), max_length)
            ]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await target.send(chunk)
                else:
                    # Thêm indicator cho phần tiếp theo
                    await target.send(f"\n{chunk}")
                # Delay nhỏ để tránh rate limit
                await asyncio.sleep(0.5)


bot = StockBot()


@bot.command(name="help")
async def help_command(ctx):
    """Hiện thị danh sách lệnh"""
    embed = discord.Embed(
        title="📊 Stock Analysis Bot - Hướng dẫn",
        description="Bot phân tích cổ phiếu Việt Nam với AI",
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="📈 Phân tích cổ phiếu",
        value="`!analysis <ticker>` - Phân tích chi tiết\nVí dụ: `!analysis VNM`",
        inline=False,
    )

    embed.add_field(
        name="💬 Hỏi đáp",
        value="`!ask <câu hỏi>` - Hỏi về cổ phiếu\nVí dụ: `!ask VNM có đáng mua hay không?`",
        inline=False,
    )

    # Thêm các field khác
    await ctx.send(embed=embed)


@bot.command(name="analysis", aliases=["analyze", "phan-tich"])
async def analysis_command(ctx, ticker: str):
    """Phân tích chi tiết cổ phiếu"""
    ticker = ticker.upper()

    async with ctx.typing():  # Hiện thị "đang gõ..."
        try:
            # Gọi AI Agent (Chạy trong thread pool để không bị block event loop)
            analysis = await asyncio.to_thread(bot.stock_agent.analyze_stock, ticker)

            # Tạo embed đẹp
            embed = discord.Embed(
                title=f"📊 Phân tích {ticker}",
                description=analysis[:4096],  # Embed limit 4096
                color=discord.Color.green(),
            )

            embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name}")

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Lỗi phân tích {ticker}: {e}", exc_info=True)
            error_msg = str(e)
            if "quota" in error_msg.lower() or "429" in error_msg:
                error_msg = "⚠️ API đã vượt quota. Vui lòng thử lại sau."
            await ctx.send(f"❌ {error_msg}")


@bot.command(name="ask", aliases=["hoi"])
async def ask_command(ctx, *, question: str):
    """Hỏi đáp tự do"""
    async with ctx.typing():
        try:
            # Chạy trong thread pool để không block event loop
            response = await asyncio.to_thread(
                bot.stock_agent.answer_question, question
            )

            # Thêm mention ở đầu
            full_response = f"{ctx.author.mention}\n{response}"

            # Gửi tin nhắn (Tự động chia nếu dài)
            await bot.send_long_message(ctx, full_response)
        except Exception as e:
            logger.error(f"Lỗi ask command: {e}", exc_info=True)
            error_msg = str(e)
            if "quota" in error_msg.lower() or "429" in error_msg:
                error_msg = "⚠️ API đã vượt quota. Vui lòng thử lại sau."
            await ctx.send(f"❌ {error_msg}")


@bot.command(name="price", aliases=["gia"])
async def price_command(ctx, ticker: str):
    """Xem giá hiện tại"""
    ticker = ticker.upper()

    async with ctx.typing():
        try:
            # lấy dữ liệu từ database
            latest_data = bot.stock_agent.db_tools.get_latest_price(ticker)

            if not latest_data:
                await ctx.send(f"❌ Không tìm thấy {ticker}")
                return

            # Tạo embed
            embed = discord.Embed(
                title=f"💰 {ticker} - Giá hiện tại", color=discord.Color.blue()
            )

            embed.add_field(
                name="Giá đóng cửa",
                value=f"**{latest_data['close']:,.0f}** VND",
                inline=False,
            )

            if latest_data.get("rsi"):
                embed.add_field(
                    name="RSI", value=f"{latest_data['rsi']:.1f}", inline=True
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Lỗi: {str(e)}")


@bot.command(name="predict", aliases=["du-doan"])
async def predict_command(ctx, ticker: str):
    """Xem dự đoán giá"""
    ticker = ticker.upper()

    async with ctx.typing():
        try:
            predictions = bot.stock_agent.db_tools.get_predictions(ticker)

            if not predictions:
                await ctx.send(f"❌ Không có dự đoán cho {ticker}")
                return

            embed = discord.Embed(
                title=f"📊 Dự đoán {ticker}", color=discord.Color.purple()
            )

            pred_text = f"Ngày 1: **{predictions['day1']*1000:,.0f}** VND\n"
            pred_text += f"Ngày 2: **{predictions['day2']*1000:,.0f}** VND\n"
            pred_text += f"Ngày 3: **{predictions['day3']*1000:,.0f}** VND"
            embed.add_field(name="3 ngày tới", value=pred_text, inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Lỗi: {str(e)}")


@bot.command(name="screener", aliases=["find", "tim"])
async def screener_command(ctx, *, criteria: str):
    """Tìm cổ phiếu theo tiêu chí"""
    async with ctx.typing():
        try:
            # Chạy trong thread pool để không block event loop
            opportunities = await asyncio.to_thread(
                bot.stock_agent.find_opportunities, criteria
            )

            embed = discord.Embed(
                title=f"🔍 Kết quả: {criteria}",
                description=opportunities[:4096],
                color=discord.Color.gold(),
            )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Lỗi: {str(e)}")


@bot.event
async def on_command_error(ctx, error):
    """Xử lý lỗi commands"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Thiếu tham số: `{error.param.name}`")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Lệnh không tồn tại. Dùng '!help`")
    else:
        logger.error(f"Lỗi: {error}")
        await ctx.send(f"❌ Lỗi: {str(error)}")


def main():
    """Chạy bot"""
    token = Config.DISCORD_BOT_TOKEN

    if not token:
        logger.error("❌ Không tìm thấy DISCORD_BOT_TOKEN")
        return

    try:
        logger.info("🚀 Đang khởi động bot...")
        bot.run(token)
    except discord.LoginFailure:
        logger.error("❌ Token không hợp lệ!")
    except Exception as e:
        logger.error(f"❌ Lỗi: {e}")


if __name__ == "__main__":
    main()
