"""
Discord Bot V3 - Gemini Version
Bot sử dụng Google Gemini với MCP Server integration
"""

import asyncio
import discord
import logging
import sys
import os
from stock_agent_gemini import GeminiStockAgent

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config import Config

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DiscordBotGemini:
    """Discord Bot với Gemini Agent và MCP Integration"""

    def __init__(
        self,
        discord_token: str,
        mcp_server_url: str = "http://localhost:5000",
        gemini_model: str = "gemini-2.5-flash-lite"
    ):
        """
        Khởi tạo Discord Bot

        Args:
            discord_token: Discord bot token
            mcp_server_url: URL của MCP server
            gemini_model: Tên model Gemini
        """
        self.discord_token = discord_token
        self.mcp_server_url = mcp_server_url
        self.gemini_model = gemini_model

        # Discord intents
        intents = discord.Intents.default()
        intents.message_content = True

        self.client = discord.Client(intents=intents)
        self.agent = None

        # Setup event handlers
        self._setup_handlers()

        logger.info("🚀 Starting Discord Bot (Gemini Version)...")
        logger.info(f"🤖 Model: {gemini_model}")
        logger.info(f"🔗 MCP Server: {mcp_server_url}")

    def _setup_handlers(self):
        """Setup Discord event handlers"""

        @self.client.event
        async def on_ready():
            """Called when bot is ready"""
            # Initialize Gemini agent
            self.agent = GeminiStockAgent(
                mcp_server_url=self.mcp_server_url,
                model_name=self.gemini_model
            )
            logger.info("✅ AI Agent (Gemini) initialized")

            # Discover tools
            logger.info("🔍 Discovering tools from MCP server...")
            tools = await self.agent.discover_tools()

            if not tools:
                logger.error("❌ No tools discovered from MCP server!")
                logger.error("Make sure MCP server is running at: " + self.mcp_server_url)
            else:
                logger.info(f"✅ Discovered {len(tools)} tools")

            logger.info(f"✅ Bot (Gemini) ready! Name: {self.client.user}")
            logger.info(f"🔗 MCP Server: {self.mcp_server_url}")

        @self.client.event
        async def on_message(message: discord.Message):
            """Handle incoming messages"""
            logger.info(f"🔔 Message received: '{message.content}' from {message.author}")

            # Ignore bot's own messages
            if message.author == self.client.user:
                logger.info("   → Ignored (own message)")
                return

            # Only respond to mentions or DMs
            if self.client.user not in message.mentions and not isinstance(
                message.channel, discord.DMChannel
            ):
                logger.info(f"   → Ignored (not mentioned, mentions: {message.mentions})")
                return

            logger.info(f"   ✅ Processing message (bot was mentioned or DM)")

            # Check if agent is ready
            if not self.agent:
                await message.channel.send("❌ Agent chưa sẵn sàng. Vui lòng đợi...")
                return

            # Extract question (remove mention)
            question = message.content
            for mention in message.mentions:
                question = question.replace(f"<@{mention.id}>", "").strip()

            if not question:
                await message.channel.send(
                    "👋 Xin chào! Tôi là Stock Bot (Gemini version). "
                    "Hãy hỏi tôi về cổ phiếu Việt Nam!\n\n"
                    "Ví dụ:\n"
                    "- `VCB giá bao nhiêu?`\n"
                    "- `Phân tích RSI của VNM`\n"
                    "- `Tìm cổ phiếu RSI dưới 30`"
                )
                return

            logger.info(f"📩 Question from {message.author}: {question}")

            # Send typing indicator
            async with message.channel.typing():
                try:
                    # Get answer from Gemini agent
                    answer = await self.agent.chat_with_tools(question)

                    # Split long messages (Discord limit: 2000 chars)
                    if len(answer) > 2000:
                        chunks = [answer[i:i+2000] for i in range(0, len(answer), 2000)]
                        for chunk in chunks:
                            await message.channel.send(chunk)
                    else:
                        await message.channel.send(answer)

                    logger.info(f"✅ Answered: {answer[:100]}...")

                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}", exc_info=True)
                    await message.channel.send(
                        f"❌ Xin lỗi, đã có lỗi xảy ra: {str(e)}"
                    )

    async def start(self):
        """Start the bot"""
        try:
            await self.client.start(self.discord_token)
        except Exception as e:
            logger.error(f"❌ Failed to start bot: {e}", exc_info=True)
            raise

    def run(self):
        """Run the bot (blocking)"""
        asyncio.run(self.start())


async def main():
    """Main function"""
    # Get config
    discord_token = Config.DISCORD_BOT_TOKEN
    mcp_server_url = "http://localhost:5000"

    if not discord_token:
        logger.error("❌ DISCORD_BOT_TOKEN not found in environment!")
        logger.error("Please set DISCORD_BOT_TOKEN in your .env file")
        return

    # Create and run bot
    bot = DiscordBotGemini(
        discord_token=discord_token,
        mcp_server_url=mcp_server_url,
        gemini_model="gemini-2.5-flash-lite"  # Có thể đổi sang "gemini-1.5-pro"
    )

    await bot.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
