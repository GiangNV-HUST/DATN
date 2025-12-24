"""
Discord Bot V3 - With MCP Agent
Bot sử dụng StockAgentV3 với MCP Integration
"""

import discord
from discord.ext import commands
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config import Config
from stock_agent_v3 import StockAgentV3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StockBotV3(commands.Bot):
    """Discord Bot V3 với MCP Agent"""

    def __init__(self, mcp_server_url: str = "http://localhost:5000"):
        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

        # Khởi tạo AI Agent V3
        self.stock_agent = StockAgentV3(mcp_server_url=mcp_server_url)
        self.mcp_server_url = mcp_server_url
        logger.info("✅ AI Agent V3 (MCP) initialized")

    async def setup_hook(self):
        """Called when bot is starting up"""
        # Discover tools từ MCP server
        logger.info("🔍 Discovering tools from MCP server...")
        tools = await self.stock_agent.discover_tools()

        if tools:
            logger.info(f"✅ Discovered {len(tools)} tools")
        else:
            logger.warning("⚠️ No tools discovered! Make sure MCP server is running.")

    async def on_ready(self):
        logger.info(f"✅ Bot V3 ready! Name: {self.user.name}")
        logger.info(f"🔗 MCP Server: {self.mcp_server_url}")

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="📈 AI Agent V3 + MCP | !help",
            )
        )

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        await self.process_commands(message)

        if self.user in message.mentions and not message.content.startswith("!"):
            await self.handle_mention(message)

    async def handle_mention(self, message: discord.Message):
        """Xử lý mention - AI tự quyết định tools via MCP"""
        content = message.content.replace(f"<@{self.user.id}>", "").strip()

        if not content:
            await message.reply(
                "Bạn cần hỏi gì về cổ phiếu? 🤔\n"
                "*Bot V3 - AI + MCP Server (Distributed Tools)*"
            )
            return

        async with message.channel.typing():
            try:
                # Gọi AI V3 - AI tự gọi MCP tools
                response = await self.stock_agent.chat_with_tools(content)
                await self.send_long_message(message.channel, response)

            except Exception as e:
                logger.error(f"Error handling mention: {e}", exc_info=True)
                error_msg = str(e)
                if "quota" in error_msg.lower() or "429" in error_msg:
                    error_msg = "⚠️ API đã vượt quota. Vui lòng thử lại sau."
                elif "connection" in error_msg.lower():
                    error_msg = "⚠️ Không kết nối được MCP server. Vui lòng kiểm tra server."
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


bot = None  # Global bot instance


@commands.command(name="help")
async def help_command(ctx):
    """Hướng dẫn sử dụng Bot V3"""
    embed = discord.Embed(
        title="📊 Stock Bot V3 - AI Agent with MCP",
        description="Bot phân tích cổ phiếu với AI + MCP Server (Distributed Tools)",
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="🆕 Điểm mới V3",
        value=(
            "✅ MCP Server - Tools phân tán\n"
            "✅ Scalable architecture\n"
            "✅ Multi-agent ready\n"
            "✅ Tool discovery tự động"
        ),
        inline=False,
    )

    embed.add_field(
        name="💬 Hỏi đáp tự nhiên",
        value="@Bot <câu hỏi> - AI tự gọi MCP tools\nVí dụ: @Bot VCB giá bao nhiêu?",
        inline=False,
    )

    embed.add_field(
        name="🔧 MCP Server",
        value=f"Status: {'🟢 Connected' if bot.stock_agent.mcp_tools else '🔴 Disconnected'}",
        inline=False,
    )

    embed.set_footer(text="V3: AI Agent + MCP Protocol | Powered by Anthropic Claude")

    await ctx.send(embed=embed)


def create_bot(mcp_server_url: str = "http://localhost:5000"):
    """Factory function to create bot"""
    global bot
    bot = StockBotV3(mcp_server_url=mcp_server_url)

    # Register commands
    bot.add_command(help_command)

    return bot


def main():
    """Chạy bot V3"""
    token = Config.DISCORD_BOT_TOKEN

    if not token:
        logger.error("❌ Không tìm thấy DISCORD_BOT_TOKEN trong .env")
        return

    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="Discord Bot V3 with MCP")
    parser.add_argument(
        "--mcp-url",
        default="http://localhost:5000",
        help="MCP Server URL (default: http://localhost:5000)"
    )
    args = parser.parse_args()

    try:
        logger.info("🚀 Starting Discord Bot V3...")
        logger.info(f"🔗 MCP Server: {args.mcp_url}")

        bot_instance = create_bot(mcp_server_url=args.mcp_url)
        bot_instance.run(token)

    except discord.LoginFailure:
        logger.error("❌ Token không hợp lệ!")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
