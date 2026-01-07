"""
Simple Discord Bot for AI Agent Hybrid System

✨ CÁCH SỬ DỤNG:
- Chỉ cần mention bot: @stock_bot <câu hỏi>
- Không cần nhớ commands phức tạp
- Bot tự động hiểu ý định và trả lời

VÍ DỤ:
- @stock_bot giá VCB
- @stock_bot phân tích HPG
- @stock_bot tìm cổ phiếu tốt
- @stock_bot với 100 triệu nên đầu tư gì
- @stock_bot so sánh VCB và ACB
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

# Import from hybrid_system database module
from hybrid_system.database import get_database_client
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SimpleStockBot(commands.Bot):
    """
    Simple Discord Bot - Chỉ cần mention để trò chuyện

    Features:
    - Natural language processing
    - AI-powered responses
    - Automatic intent detection
    - Rich embeds
    - Conversation memory
    """

    def __init__(self):
        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True

        # Initialize bot (prefix không quan trọng vì dùng mention)
        super().__init__(
            command_prefix="!",  # Backup only
            intents=intents,
            help_command=None
        )

        # Initialize database client
        self.db = get_database_client()
        logger.info("✅ Database client initialized")

        # Configure OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.ai_client = OpenAI(api_key=openai_key)
            self.ai_model = "gpt-4o-mini"  # Fast and cost-effective model
            logger.info("✅ OpenAI initialized with model: " + self.ai_model)
        else:
            self.ai_client = None
            self.ai_model = None
            logger.warning("⚠️ OPENAI_API_KEY not found - AI features disabled")

        # Conversation memory (user_id -> last 5 messages)
        self.conversations: Dict[int, list] = {}

        # Track active queries
        self.active_queries: set = set()

        # Statistics
        self.stats = {
            "total_queries": 0,
            "price_queries": 0,
            "analysis_queries": 0,
            "screener_queries": 0,
            "investment_queries": 0,
            "general_queries": 0,
            "errors": 0,
            "start_time": datetime.now()
        }

        logger.info("✅ Simple Stock Bot initialized")

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"🤖 Bot ready! Logged in as {self.user.name}")

        # Set bot presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="@stock_bot <câu hỏi>"
            )
        )

        logger.info(f"📡 Serving {len(self.guilds)} servers")

    async def on_message(self, message: discord.Message):
        """Handle ALL messages - chỉ cần mention là được"""
        # Debug: Log every message received
        logger.info(f"🔔 on_message event triggered - Author: {message.author.name}, Message ID: {message.id}")

        # Ignore bot's own messages
        if message.author == self.user:
            logger.info(f"⏭️ Ignoring bot's own message (ID: {message.id})")
            return

        # Check if bot is mentioned
        if self.user in message.mentions:
            logger.info(f"✅ Bot mentioned in message ID: {message.id}")
            await self.handle_conversation(message)

        # Still support ! commands as backup
        elif message.content.startswith("!"):
            await self.process_commands(message)

    async def handle_conversation(self, message: discord.Message):
        """
        Main conversation handler - Xử lý TẤT CẢ câu hỏi
        Tự động detect intent và route đến handler phù hợp
        """
        # Debug: Log incoming message
        logger.info(f"📨 Message from {message.author.name} (ID: {message.author.id}): {message.content}")

        # Get clean content (remove mention)
        content = message.content
        for mention in message.mentions:
            content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
        content = content.strip()

        logger.info(f"🔍 Cleaned query: '{content}'")

        if not content:
            logger.info(f"⚠️ Empty content, sending help message")
            await message.channel.send(
                "Xin chào! 👋\n\n"
                "Tôi là bot phân tích chứng khoán. Bạn có thể hỏi tôi:\n"
                "• Giá cổ phiếu: `@stock_bot giá VCB`\n"
                "• Phân tích: `@stock_bot phân tích HPG`\n"
                "• Tìm kiếm: `@stock_bot tìm cổ phiếu tốt`\n"
                "• Tư vấn: `@stock_bot với 100 triệu nên đầu tư gì`\n"
                "• Bất kỳ câu hỏi nào về chứng khoán!"
            )
            return

        # Check if user has active query
        user_id = str(message.author.id)
        logger.info(f"🔑 User ID: {user_id}, Active queries: {self.active_queries}")
        if user_id in self.active_queries:
            logger.info(f"⏸️ User {user_id} has active query, rejecting")
            await message.channel.send("⏳ Đang xử lý câu hỏi trước của bạn, vui lòng đợi...")
            return

        # Mark as active
        logger.info(f"✅ Marking user {user_id} as active")
        self.active_queries.add(user_id)

        try:
            logger.info(f"💬 Processing query (NO typing indicator)")
            # Process the query WITHOUT typing indicator to test
            logger.info(f"🔄 Starting process_natural_query for: {content}")
            response = await self.process_natural_query(content, message.author.id)
            logger.info(f"✅ Finished process_natural_query, response type: {type(response)}, length: {len(response) if response else 0}")

            # Update stats
            self.stats["total_queries"] += 1

            # Debug: Log response before sending
            logger.info(f"📤 Sending response (length: {len(response)}): {response[:100]}...")
            logger.info(f"📝 Full response:\n{response}")

            # Send response
            if len(response) <= 2000:
                # Send without reference to avoid Discord API bug
                sent_msg = await message.channel.send(response)
                logger.info(f"✉️ Sent single message to channel, message ID: {sent_msg.id}")
            else:
                # Split long messages
                chunks = self.split_message(response, 2000)
                await message.channel.send(chunks[0])
                logger.info(f"✉️ Sent first chunk")
                for chunk in chunks[1:]:
                    await message.channel.send(chunk)
                    await asyncio.sleep(0.5)
                    logger.info(f"✉️ Sent additional chunk")

        except Exception as e:
            logger.error(f"❌ Error handling conversation: {e}", exc_info=True)
            self.stats["errors"] += 1

            error_msg = "Xin lỗi, đã có lỗi xảy ra khi xử lý câu hỏi của bạn."
            if "quota" in str(e).lower():
                error_msg = "⚠️ API đã vượt quota. Vui lòng thử lại sau."
            elif "timeout" in str(e).lower():
                error_msg = "⏱️ Timeout. Vui lòng thử lại với câu hỏi đơn giản hơn."

            await message.channel.send(error_msg)

        finally:
            # Remove from active queries
            self.active_queries.discard(user_id)

    async def process_natural_query(self, query: str, user_id: int) -> str:
        """
        Process natural language query using LLM
        LLM sẽ hiểu câu hỏi và truy vấn database phù hợp
        """
        # Store in conversation memory
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        self.conversations[user_id].append({
            "role": "user",
            "content": query,
            "timestamp": datetime.now()
        })
        # Keep only last 5 messages
        self.conversations[user_id] = self.conversations[user_id][-5:]

        # Update total queries
        self.stats["total_queries"] += 1

        # Use LLM to understand query and respond
        return await self.handle_llm_query(query, user_id)

    def detect_intent(self, query: str) -> str:
        """
        Detect user intent from query
        Returns: price, analysis, screener, investment, compare, general
        """
        # Price query
        if any(word in query for word in ['giá', 'gia', 'price', 'bao nhiêu', 'bao nhieu']):
            return "price"

        # Analysis query
        if any(word in query for word in ['phân tích', 'phan tich', 'analyze', 'analysis', 'đánh giá', 'danh gia', 'nhận xét', 'nhan xet']):
            return "analysis"

        # Screener query
        if any(word in query for word in ['tìm', 'tim', 'find', 'search', 'screener', 'lọc', 'loc', 'danh sách', 'danh sach']):
            return "screener"

        # Investment query
        if any(word in query for word in ['đầu tư', 'dau tu', 'invest', 'mua', 'buy', 'nên', 'nen', 'khuyến nghị', 'khuyen nghi', 'portfolio', 'danh mục', 'danh muc']):
            return "investment"

        # Compare query
        if any(word in query for word in ['so sánh', 'so sanh', 'compare', 'vs', 'hay', 'tốt hơn', 'tot hon']):
            return "compare"

        # Default
        return "general"

    async def handle_price_query(self, query: str) -> str:
        """Handle price queries"""
        ticker = self.extract_ticker(query)

        if not ticker:
            return (
                "🤔 Bạn muốn xem giá cổ phiếu nào?\n\n"
                "Ví dụ: `@stock_bot giá VCB`"
            )

        try:
            price_data = self.db.get_latest_price(ticker)

            if not price_data:
                return f"❌ Không tìm thấy dữ liệu cho {ticker}"

            # Format response
            response = f"📊 **{ticker} - GIÁ HIỆN TẠI**\n\n"

            close = price_data.get('close', 0)
            response += f"💰 **Giá đóng cửa**: {close:,.0f} VND\n"

            if price_data.get('volume'):
                volume = price_data['volume']
                response += f"📈 **Khối lượng**: {volume:,.0f}\n"

            if price_data.get('change_percent'):
                change = price_data['change_percent']
                emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
                response += f"{emoji} **Thay đổi**: {change:+.2f}%\n"

            response += "\n**Chỉ báo kỹ thuật:**\n"

            if price_data.get('rsi'):
                rsi = price_data['rsi']
                rsi_status = "Quá mua ⚠️" if rsi > 70 else "Quá bán 💡" if rsi < 30 else "Trung bình"
                response += f"• RSI: {rsi:.1f} ({rsi_status})\n"

            if price_data.get('ma20'):
                ma20 = price_data['ma20']
                trend = "Tăng 📈" if close > ma20 else "Giảm 📉"
                response += f"• MA20: {ma20:,.0f} VND ({trend})\n"

            if price_data.get('macd'):
                macd = price_data['macd']
                response += f"• MACD: {macd:.2f}\n"

            response += f"\n_Cập nhật: {price_data.get('date', 'N/A')}_"

            return response

        except Exception as e:
            logger.error(f"Error in price query: {e}")
            return f"❌ Lỗi khi lấy giá {ticker}: {str(e)}"

    async def handle_analysis_query(self, query: str) -> str:
        """Handle analysis queries"""
        ticker = self.extract_ticker(query)

        if not ticker:
            return (
                "🤔 Bạn muốn phân tích cổ phiếu nào?\n\n"
                "Ví dụ: `@stock_bot phân tích HPG`"
            )

        try:
            # Get comprehensive data
            price_data = self.db.get_latest_price(ticker)
            history = self.db.get_price_history(ticker, days=30)

            if not price_data:
                return f"❌ Không tìm thấy dữ liệu cho {ticker}"

            # Format analysis
            response = f"📊 **PHÂN TÍCH {ticker}**\n\n"

            # Current price
            close = price_data.get('close', 0)
            response += f"💰 **Giá hiện tại**: {close:,.0f} VND\n\n"

            # Technical indicators
            response += "**📈 CHỈ BÁO KỸ THUẬT:**\n"

            if price_data.get('rsi'):
                rsi = price_data['rsi']
                response += f"• **RSI**: {rsi:.1f}"
                if rsi > 70:
                    response += " ⚠️ QUÁ MUA - Cẩn thận khi mua thêm\n"
                elif rsi < 30:
                    response += " 💡 QUÁ BÁN - Có thể là cơ hội mua\n"
                else:
                    response += " ✅ Ở mức trung bình\n"

            if price_data.get('ma20'):
                ma20 = price_data['ma20']
                response += f"• **MA20**: {ma20:,.0f} VND"
                if close > ma20:
                    response += " 📈 Giá trên MA20 (tích cực)\n"
                else:
                    response += " 📉 Giá dưới MA20 (tiêu cực)\n"

            if price_data.get('macd'):
                macd = price_data['macd']
                response += f"• **MACD**: {macd:.2f}"
                response += " 🟢 Tích cực\n" if macd > 0 else " 🔴 Tiêu cực\n"

            # Price trend
            if history and len(history) >= 5:
                response += "\n**📊 XU HƯỚNG GIÁ:**\n"
                recent_prices = [h['close'] for h in history[:5]]

                if recent_prices[0] > recent_prices[-1]:
                    trend_pct = ((recent_prices[0] - recent_prices[-1]) / recent_prices[-1]) * 100
                    response += f"• 5 ngày gần đây: **Tăng** {trend_pct:.1f}% 📈\n"
                else:
                    trend_pct = ((recent_prices[-1] - recent_prices[0]) / recent_prices[0]) * 100
                    response += f"• 5 ngày gần đây: **Giảm** {trend_pct:.1f}% 📉\n"

            # Recommendation hint
            response += "\n**💡 GỢI Ý:**\n"
            if price_data.get('rsi', 50) < 30:
                response += "• RSI thấp - có thể xem xét mua khi có tín hiệu tích cực khác\n"
            elif price_data.get('rsi', 50) > 70:
                response += "• RSI cao - nên thận trọng, có thể chốt lời nếu đã nắm giữ\n"
            else:
                response += "• Theo dõi thêm các chỉ báo khác trước khi quyết định\n"

            response += f"\n_Dữ liệu cập nhật: {price_data.get('date', 'N/A')}_"

            return response

        except Exception as e:
            logger.error(f"Error in analysis query: {e}")
            return f"❌ Lỗi khi phân tích {ticker}: {str(e)}"

    async def handle_screener_query(self, query: str) -> str:
        """Handle stock screening queries"""
        try:
            # Parse criteria from query
            criteria = {}
            query_lower = query.lower()

            # RSI criteria
            if 'rsi' in query_lower and ('thấp' in query_lower or 'thap' in query_lower or 'low' in query_lower):
                criteria['rsi_below'] = 40
            elif 'rsi' in query_lower and ('cao' in query_lower or 'high' in query_lower):
                criteria['rsi_above'] = 60

            # PE criteria
            if 'pe' in query_lower and ('thấp' in query_lower or 'thap' in query_lower or 'low' in query_lower):
                criteria['pe_below'] = 15

            # Default: find undervalued stocks
            if not criteria:
                criteria = {'rsi_below': 50, 'limit': 10}

            # Search stocks
            stocks = self.db.search_stocks_by_criteria(criteria)

            if not stocks or len(stocks) == 0:
                return "❌ Không tìm thấy cổ phiếu nào phù hợp với tiêu chí."

            # Format response
            response = f"🔍 **TÌM THẤY {len(stocks)} CỔ PHIẾU**\n\n"

            for i, stock in enumerate(stocks[:15], 1):
                ticker = stock.get('ticker', 'N/A')
                price = stock.get('close', 0)
                rsi = stock.get('rsi', 0)

                response += f"{i}. **{ticker}**: {price:,.0f} VND"

                if rsi:
                    response += f" | RSI: {rsi:.1f}"
                    if rsi < 30:
                        response += " 💡"
                    elif rsi > 70:
                        response += " ⚠️"

                response += "\n"

            response += "\n💡 Gợi ý: Dùng `@stock_bot phân tích <mã>` để xem chi tiết từng cổ phiếu"

            return response

        except Exception as e:
            logger.error(f"Error in screener query: {e}")
            return f"❌ Lỗi khi tìm kiếm: {str(e)}"

    async def handle_investment_query(self, query: str) -> str:
        """Handle investment recommendation queries"""
        try:
            # Extract amount from query
            import re
            amount_match = re.search(r'(\d+)\s*(triệu|trieu|million|tr)', query.lower())

            if amount_match:
                amount = int(amount_match.group(1)) * 1_000_000
            else:
                amount = 100_000_000  # Default 100 million

            # Get good stocks
            stocks = self.db.search_stocks_by_criteria({
                'rsi_below': 50,
                'limit': 10
            })

            if not stocks or len(stocks) < 3:
                return "❌ Không đủ dữ liệu để tư vấn đầu tư. Vui lòng thử lại sau."

            # Use AI to generate recommendation if available
            if self.ai_client:
                # Prepare context
                context = f"Nhà đầu tư có {amount/1_000_000:.0f} triệu VND.\n\n"
                context += "Các cổ phiếu tiềm năng:\n"

                for stock in stocks[:5]:
                    ticker = stock.get('ticker')
                    price = stock.get('close', 0)
                    rsi = stock.get('rsi', 0)
                    context += f"- {ticker}: {price:,.0f} VND, RSI: {rsi:.1f}\n"

                # Generate AI recommendation using OpenAI
                prompt = f"""{context}

Hãy đưa ra lời khuyên đầu tư ngắn gọn (200 từ):
1. Nên chọn 2-3 cổ phiếu nào
2. Phân bổ vốn như thế nào
3. Lý do ngắn gọn
4. Rủi ro cần lưu ý

Trả lời bằng tiếng Việt, ngắn gọn, dễ hiểu."""

                try:
                    completion = self.ai_client.chat.completions.create(
                        model=self.ai_model,
                        messages=[
                            {"role": "system", "content": "Bạn là chuyên gia tư vấn đầu tư chứng khoán Việt Nam."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=500,
                        temperature=0.7
                    )
                    ai_text = completion.choices[0].message.content
                    response = f"💰 **TƯ VẤN ĐẦU TƯ CHO {amount/1_000_000:.0f} TRIỆU VND**\n\n"
                    response += ai_text
                    return response
                except Exception as e:
                    logger.error(f"AI generation error: {e}")
                    # Fallback to simple recommendation

            # Simple recommendation (fallback)
            response = f"💰 **TƯ VẤN ĐẦU TƯ CHO {amount/1_000_000:.0f} TRIỆU VND**\n\n"
            response += "**Gợi ý phân bổ:**\n"

            top3 = stocks[:3]
            allocation = [0.4, 0.35, 0.25]  # 40%, 35%, 25%

            for i, (stock, pct) in enumerate(zip(top3, allocation), 1):
                ticker = stock.get('ticker')
                price = stock.get('close', 0)
                invest_amount = amount * pct
                shares = int(invest_amount / (price * 100)) * 100  # Round to 100

                response += f"\n{i}. **{ticker}** ({pct*100:.0f}%):\n"
                response += f"   • Vốn: {invest_amount/1_000_000:.1f} triệu\n"
                response += f"   • Giá: {price:,.0f} VND\n"
                response += f"   • Số lượng: ~{shares:,} cổ phiếu\n"

            response += "\n⚠️ **Lưu ý**: Đây chỉ là gợi ý. Hãy tự nghiên cứu kỹ trước khi đầu tư."

            return response

        except Exception as e:
            logger.error(f"Error in investment query: {e}")
            return f"❌ Lỗi khi tư vấn đầu tư: {str(e)}"

    async def handle_ai_query(self, query: str, user_id: int) -> str:
        """Handle general queries with AI"""
        if not self.ai_client:
            return (
                "🤖 Tính năng AI chưa được kích hoạt.\n\n"
                "Bạn có thể hỏi tôi về:\n"
                "• Giá cổ phiếu\n"
                "• Phân tích kỹ thuật\n"
                "• Tìm kiếm cổ phiếu\n"
                "• Tư vấn đầu tư"
            )

        try:
            # Get conversation history
            history = self.conversations.get(user_id, [])

            # Build messages for OpenAI
            messages = [
                {"role": "system", "content": "Bạn là chuyên gia phân tích chứng khoán Việt Nam. Trả lời ngắn gọn (100-150 từ), hữu ích và chuyên nghiệp bằng tiếng Việt. Nếu cần thông tin cụ thể về một cổ phiếu, gợi ý user dùng @stock_bot <lệnh cụ thể>."}
            ]

            # Add conversation history (last 3 messages)
            for msg in history[-3:]:
                role = "assistant" if msg['role'] == "assistant" else "user"
                messages.append({"role": role, "content": msg['content']})

            # Add current query
            messages.append({"role": "user", "content": query})

            # Generate response using OpenAI
            completion = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )

            ai_text = completion.choices[0].message.content

            # Store AI response in conversation
            self.conversations[user_id].append({
                "role": "assistant",
                "content": ai_text,
                "timestamp": datetime.now()
            })

            return ai_text

        except Exception as e:
            logger.error(f"AI query error: {e}")
            return (
                "❌ Không thể xử lý câu hỏi này bằng AI.\n\n"
                "Bạn có thể thử:\n"
                "• `@stock_bot giá <mã>`\n"
                "• `@stock_bot phân tích <mã>`\n"
                "• `@stock_bot tìm cổ phiếu tốt`"
            )

    def extract_ticker(self, text: str) -> Optional[str]:
        """Extract stock ticker from text"""
        # Vietnamese stock tickers: 3-4 uppercase letters
        match = re.search(r'\b([A-Z]{3,4})\b', text.upper())
        return match.group(1) if match else None

    async def handle_llm_query(self, query: str, user_id: int) -> str:
        """
        Use LLM to understand query and provide intelligent response
        LLM will analyze query, determine what data is needed, and format response
        """
        if not self.ai_client:
            return "🤖 Tính năng AI chưa được kích hoạt. Vui lòng kiểm tra OPENAI_API_KEY."

        try:
            # Get available stocks from database
            available_stocks = self.db.search_stocks_by_criteria({'limit': 100})
            stock_tickers = [s.get('ticker') for s in available_stocks] if available_stocks else []

            # Get conversation history
            history = self.conversations.get(user_id, [])

            # Build context-aware prompt
            system_prompt = f"""Bạn là chuyên gia phân tích chứng khoán Việt Nam với khả năng truy cập database.

CÁC MÃ CỔ PHIẾU CÓ SẴN: {', '.join(stock_tickers[:15])}

NHIỆM VỤ CỦA BẠN:
1. Hiểu câu hỏi của người dùng (có thể tiếng Việt hoặc English)
2. Xác định mã cổ phiếu được hỏi (nếu có)
3. Quyết định cần truy vấn dữ liệu gì
4. Trả lời câu hỏi một cách chuyên nghiệp

KHẢ NĂNG CỦA BẠN:
- Lấy giá cổ phiếu hiện tại với các chỉ báo kỹ thuật (RSI, MA20, MACD)
- Phân tích kỹ thuật chi tiết
- Tìm kiếm cổ phiếu theo tiêu chí
- Tư vấn đầu tư
- So sánh cổ phiếu
- Trả lời câu hỏi chung về chứng khoán

HƯỚNG DẪN TRẢ LỜI:
- Nếu người dùng hỏi về GIÁ (VD: "giá VCB", "VCB bao nhiêu"):
  Trả về JSON {{"action": "get_price", "ticker": "MÃ_CP"}}

- Nếu người dùng muốn XEM BIỂU ĐỒ (VD: "biểu đồ VIC", "chart HPG", "xem đồ thị FPT 30 ngày"):
  Trả về JSON {{"action": "get_chart", "ticker": "MÃ_CP", "days": số_ngày}}
  ⚠️ days mặc định là 30 nếu không đề cập

- Nếu người dùng hỏi về CHỈ SỐ CƠ BẢN/TÀI CHÍNH (VD: "P/E của VCB", "EPS HPG", "ROE VNM", "định giá FPT"):
  Trả về JSON {{"action": "get_fundamentals", "ticker": "MÃ_CP", "metrics": ["P/E", "EPS", "ROE"]}}
  ⚠️ metrics là danh sách chỉ số được hỏi (P/E, EPS, ROE, ROA, Debt/Equity, v.v.)

- Nếu người dùng muốn PHÂN TÍCH hoặc hỏi NÊN MUA KHÔNG (VD: "phân tích HPG", "HPG có nên mua không", "VCB nên mua không"):
  Trả về JSON {{"action": "analyze", "ticker": "MÃ_CP"}}
  ⚠️ QUAN TRỌNG: Câu hỏi dạng "X có nên mua không?" là yêu cầu PHÂN TÍCH, KHÔNG PHẢI tư vấn đầu tư

- Nếu người dùng muốn TÌM KIẾM:
  Trả về JSON {{"action": "screener", "criteria": "mô tả tiêu chí"}}

- Nếu người dùng muốn TƯ VẤN ĐẦU TƯ (phải có ĐỀ CẬP SỐ TIỀN cụ thể):
  + Có đề cập cổ phiếu cụ thể (VD: "100 triệu vào FPT và HPG", "đầu tư 50 triệu vào VCB"):
    {{"action": "invest", "amount": số_tiền, "tickers": ["FPT", "HPG"]}}
  + Không đề cập cổ phiếu (VD: "100 triệu nên đầu tư gì", "50 triệu đầu tư vào đâu"):
    {{"action": "invest", "amount": số_tiền}}
  ⚠️ CHỈ dùng "invest" khi người dùng ĐỀ CẬP SỐ TIỀN (100 triệu, 50 triệu, v.v.)

- Nếu người dùng muốn SO SÁNH:
  Trả về JSON {{"action": "compare", "tickers": ["MÃ1", "MÃ2"]}}

- Nếu người dùng muốn TẠO CẢNH BÁO GIÁ (VD: "cảnh báo khi VIC lên 100k", "báo cho tôi khi HPG xuống 50000"):
  Trả về JSON {{"action": "create_alert", "ticker": "MÃ_CP", "condition": ">"|"<"|">="|"<=", "price": giá_mục_tiêu}}
  ⚠️ condition: ">" (lên trên), "<" (xuống dưới), ">=" (lên từ), "<=" (xuống từ)

- Nếu người dùng muốn XEM CẢNH BÁO (VD: "xem cảnh báo của tôi", "danh sách alert"):
  Trả về JSON {{"action": "list_alerts"}}

- Nếu người dùng muốn XÓA CẢNH BÁO (VD: "xóa cảnh báo số 1", "hủy alert 2"):
  Trả về JSON {{"action": "delete_alert", "alert_id": số_thứ_tự}}

- Nếu người dùng muốn PHÂN TÍCH NẾN NHẬT/CANDLESTICK (VD: "phân tích nến HPG", "candlestick VCB", "nến nhật FPT tuần này"):
  Trả về JSON {{"action": "candlestick_analysis", "ticker": "MÃ_CP", "days": số_ngày}}
  ⚠️ days mặc định là 7 (1 tuần) nếu không đề cập

- Nếu người dùng muốn PHÂN TÍCH DANH MỤC/PORTFOLIO (VD: "danh mục VNM 100 cổ VCB 50 cổ", "portfolio HPG 200 FPT 150"):
  Trả về JSON {{"action": "portfolio_analysis", "holdings": [{{"ticker": "VNM", "quantity": 100}}, {{"ticker": "VCB", "quantity": 50}}]}}

- Nếu người dùng muốn THEO DÕI cổ phiếu (VD: "theo dõi VNM", "subscribe HPG", "follow FPT"):
  Trả về JSON {{"action": "subscribe", "ticker": "MÃ_CP"}}

- Nếu người dùng muốn XEM DANH SÁCH THEO DÕI (VD: "xem theo dõi", "danh sách subscribe", "cổ phiếu đang follow"):
  Trả về JSON {{"action": "list_subscriptions"}}

- Nếu người dùng muốn HỦY THEO DÕI (VD: "hủy theo dõi VNM", "unsubscribe HPG", "bỏ follow FPT"):
  Trả về JSON {{"action": "unsubscribe", "ticker": "MÃ_CP"}}

- Nếu là CÂU HỎI CHUNG:
  Trả về JSON {{"action": "general", "question": "câu hỏi"}}

LƯU Ý QUAN TRỌNG:
- Luôn trả về JSON hợp lệ
- Mã cổ phiếu phải viết HOA (VD: VCB, HPG, VNM, FPT)
- QUAN TRỌNG: Tìm TẤT CẢ các mã cổ phiếu trong câu hỏi (FPT, HPG, VCB, v.v.) và đưa vào mảng "tickers"
- Số tiền: 100 triệu = 100000000, 50 triệu = 50000000, 200 triệu = 200000000
- amount phải là số nguyên, tính bằng VND (không có dấu phẩy)
- ⚠️ KHI KHÔNG CÓ DỮ LIỆU: Hệ thống sẽ tự động trả lời "không có dữ liệu" khi database không có thông tin
  KHÔNG bao giờ tự bịa đặt hoặc ước tính số liệu khi không có dữ liệu thực tế"""

            # Build messages with history
            messages = [{"role": "system", "content": system_prompt}]

            # Add recent conversation (last 2 exchanges)
            for msg in history[-4:]:
                role = "assistant" if msg['role'] == "assistant" else "user"
                messages.append({"role": role, "content": msg['content']})

            # Add current query
            messages.append({"role": "user", "content": query})

            # Get LLM decision
            completion = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=messages,
                max_tokens=200,
                temperature=0.3,  # Lower temperature for more consistent JSON
                response_format={"type": "json_object"}
            )

            llm_response = completion.choices[0].message.content

            # Debug: Log LLM response
            logger.info(f"🤖 LLM Response: {llm_response}")

            # Parse LLM decision
            import json
            decision = json.loads(llm_response)
            action = decision.get('action', 'general')

            # Debug: Log parsed decision
            logger.info(f"📊 Parsed Decision - Action: {action}, Tickers: {decision.get('tickers', [])}, Amount: {decision.get('amount', 0)}")

            # Route to appropriate handler based on LLM decision
            if action == 'get_price':
                ticker = decision.get('ticker', '').upper()
                if ticker:
                    self.stats["price_queries"] += 1
                    return await self.handle_price_query_llm(ticker)
                else:
                    return "🤔 Bạn muốn xem giá cổ phiếu nào? Ví dụ: VCB, HPG, VNM"

            elif action == 'analyze':
                ticker = decision.get('ticker', '').upper()
                if ticker:
                    self.stats["analysis_queries"] += 1
                    return await self.handle_analysis_query_llm(ticker)
                else:
                    return "🤔 Bạn muốn phân tích cổ phiếu nào?"

            elif action == 'screener':
                self.stats["screener_queries"] += 1
                criteria = decision.get('criteria', '')
                return await self.handle_screener_query_llm(criteria)

            elif action == 'invest':
                self.stats["investment_queries"] += 1
                amount = decision.get('amount', 100000000)
                tickers = decision.get('tickers', [])  # Extract tickers if mentioned
                return await self.handle_investment_query_llm(amount, query, tickers)

            elif action == 'get_chart':
                ticker = decision.get('ticker', '').upper()
                days = decision.get('days', 30)
                if ticker:
                    self.stats["general_queries"] += 1
                    return await self.handle_chart_request(ticker, days)
                else:
                    return "🤔 Bạn muốn xem biểu đồ cổ phiếu nào?"

            elif action == 'get_fundamentals':
                ticker = decision.get('ticker', '').upper()
                metrics = decision.get('metrics', [])
                if ticker:
                    self.stats["general_queries"] += 1
                    return await self.handle_fundamentals_request(ticker, metrics)
                else:
                    return "🤔 Bạn muốn xem chỉ số tài chính của cổ phiếu nào?"

            elif action == 'compare':
                tickers = decision.get('tickers', [])
                if len(tickers) >= 2:
                    self.stats["general_queries"] += 1
                    return await self.handle_compare_query_llm(tickers)
                else:
                    return "🤔 Bạn muốn so sánh ít nhất 2 cổ phiếu."

            elif action == 'create_alert':
                ticker = decision.get('ticker', '').upper()
                condition = decision.get('condition', '>')
                price = decision.get('price', 0)
                if ticker and price > 0:
                    return await self.handle_create_alert(user_id, ticker, condition, price)
                else:
                    return "🤔 Vui lòng cung cấp đầy đủ: mã cổ phiếu, điều kiện (>, <) và giá mục tiêu."

            elif action == 'list_alerts':
                return await self.handle_list_alerts(user_id)

            elif action == 'delete_alert':
                alert_id = decision.get('alert_id', 0)
                if alert_id > 0:
                    return await self.handle_delete_alert(user_id, alert_id)
                else:
                    return "🤔 Vui lòng cung cấp ID cảnh báo cần xóa."

            elif action == 'candlestick_analysis':
                ticker = decision.get('ticker', '').upper()
                days = decision.get('days', 7)
                if ticker:
                    self.stats["general_queries"] += 1
                    return await self.handle_candlestick_analysis(ticker, days)
                else:
                    return "🤔 Bạn muốn phân tích nến Nhật của cổ phiếu nào?"

            elif action == 'portfolio_analysis':
                holdings = decision.get('holdings', [])
                if holdings and len(holdings) > 0:
                    self.stats["general_queries"] += 1
                    return await self.handle_portfolio_analysis(holdings)
                else:
                    return "🤔 Vui lòng cung cấp danh mục cổ phiếu của bạn. VD: 'danh mục VNM 100 cổ, VCB 50 cổ'"

            elif action == 'subscribe':
                ticker = decision.get('ticker', '').upper()
                if ticker:
                    return await self.handle_subscribe(user_id, ticker)
                else:
                    return "🤔 Bạn muốn theo dõi cổ phiếu nào?"

            elif action == 'list_subscriptions':
                return await self.handle_list_subscriptions(user_id)

            elif action == 'unsubscribe':
                ticker = decision.get('ticker', '').upper()
                if ticker:
                    return await self.handle_unsubscribe(user_id, ticker)
                else:
                    return "🤔 Bạn muốn hủy theo dõi cổ phiếu nào?"

            else:
                # General question - use AI to answer
                self.stats["general_queries"] += 1
                return await self.handle_general_llm(query, user_id)

        except Exception as e:
            logger.error(f"LLM query error: {e}", exc_info=True)
            return f"❌ Đã có lỗi khi xử lý câu hỏi: {str(e)}\n\nBạn có thể thử lại hoặc hỏi câu khác."

    async def handle_price_query_llm(self, ticker: str) -> str:
        """Get price data for ticker (LLM version)"""
        try:
            price_data = self.db.get_latest_price(ticker)
            if not price_data:
                return f"❌ Không tìm thấy dữ liệu cho {ticker}"

            response = f"📊 {ticker} - GIÁ HIỆN TẠI\n\n"
            response += f"💰 Giá đóng cửa: {price_data.get('close', 0):,.0f} VND\n"

            if price_data.get('volume'):
                response += f"📈 Khối lượng: {price_data['volume']:,.0f}\n"

            if price_data.get('change_percent'):
                change = price_data['change_percent']
                emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
                response += f"{emoji} Thay đổi: {change:+.2f}%\n"

            response += "\nChỉ báo kỹ thuật:\n"

            if price_data.get('rsi'):
                rsi = price_data['rsi']
                rsi_status = "Quá mua ⚠️" if rsi > 70 else "Quá bán 💡" if rsi < 30 else "Trung bình"
                response += f"• RSI: {rsi:.1f} ({rsi_status})\n"

            if price_data.get('ma20'):
                ma20 = price_data['ma20']
                trend = "Tăng 📈" if price_data.get('close', 0) > ma20 else "Giảm 📉"
                response += f"• MA20: {ma20:,.0f} VND ({trend})\n"

            if price_data.get('macd'):
                response += f"• MACD: {price_data['macd']:.2f}\n"

            return response

        except Exception as e:
            return f"❌ Lỗi khi lấy giá {ticker}: {str(e)}"

    async def handle_analysis_query_llm(self, ticker: str) -> str:
        """Analyze ticker (LLM version)"""
        try:
            price_data = self.db.get_latest_price(ticker)
            history = self.db.get_price_history(ticker, days=30)

            if not price_data:
                return f"❌ Không tìm thấy dữ liệu cho {ticker}"

            response = f"📊 **PHÂN TÍCH {ticker}**\n\n"
            response += f"💰 **Giá hiện tại**: {price_data.get('close', 0):,.0f} VND\n\n"
            response += "**📈 CHỈ BÁO KỸ THUẬT:**\n"

            # Collect signals for recommendation
            buy_signals = 0
            sell_signals = 0
            neutral_signals = 0

            if price_data.get('rsi'):
                rsi = price_data['rsi']
                response += f"• **RSI**: {rsi:.1f}"
                if rsi > 70:
                    response += " ⚠️ QUÁ MUA - Cẩn thận\n"
                    sell_signals += 1
                elif rsi < 30:
                    response += " 💡 QUÁ BÁN - Cơ hội mua\n"
                    buy_signals += 1
                else:
                    response += " ✅ Ở mức trung bình\n"
                    neutral_signals += 1

            if price_data.get('ma20'):
                ma20 = price_data['ma20']
                close = price_data.get('close', 0)
                response += f"• **MA20**: {ma20:,.0f} VND"
                if close > ma20:
                    response += " 📈 Tích cực (Giá trên MA20)\n"
                    buy_signals += 1
                else:
                    response += " 📉 Tiêu cực (Giá dưới MA20)\n"
                    sell_signals += 1

            if price_data.get('macd'):
                macd = price_data['macd']
                response += f"• **MACD**: {macd:.2f}"
                if macd > 0:
                    response += " 🟢 Tích cực\n"
                    buy_signals += 1
                else:
                    response += " 🔴 Tiêu cực\n"
                    sell_signals += 1

            if history and len(history) >= 5:
                response += "\n**📊 XU HƯỚNG GIÁ:**\n"
                recent = [h['close'] for h in history[:5]]
                if recent[0] > recent[-1]:
                    pct = ((recent[0] - recent[-1]) / recent[-1]) * 100
                    response += f"• 5 ngày: **Tăng** {pct:.1f}% 📈\n"
                    buy_signals += 1
                else:
                    pct = ((recent[-1] - recent[0]) / recent[0]) * 100
                    response += f"• 5 ngày: **Giảm** {pct:.1f}% 📉\n"
                    sell_signals += 1

            # Add recommendation
            response += "\n**💡 KHUYẾN NGHỊ:**\n"
            if buy_signals > sell_signals:
                response += f"✅ **NÊN MUA** - Có {buy_signals} tín hiệu tích cực\n"
                response += "Cổ phiếu đang có xu hướng tốt, phù hợp để mua vào.\n"
            elif sell_signals > buy_signals:
                response += f"⚠️ **CHƯA NÊN MUA** - Có {sell_signals} tín hiệu tiêu cực\n"
                response += "Nên đợi tín hiệu tốt hơn trước khi mua.\n"
            else:
                response += "⚪ **TRUNG LẬP** - Cân nhắc kỹ trước khi quyết định\n"
                response += "Tín hiệu chưa rõ ràng, cần theo dõi thêm.\n"

            response += "\n_⚠️ Đây chỉ là phân tích kỹ thuật, không phải lời khuyên tài chính._"

            return response

        except Exception as e:
            return f"❌ Lỗi khi phân tích {ticker}: {str(e)}"

    async def handle_screener_query_llm(self, criteria_text: str) -> str:
        """Screen stocks (LLM version)"""
        try:
            # Parse criteria
            criteria_lower = criteria_text.lower()
            limit = 10  # Default limit

            # Extract number if specified (e.g., "5 cổ phiếu")
            import re
            num_match = re.search(r'(\d+)\s*(?:cổ\s*phiếu|cp|stock)', criteria_lower)
            if num_match:
                limit = int(num_match.group(1))

            # Check for momentum query
            is_momentum = any(word in criteria_lower for word in ['momentum', 'tăng mạnh', 'tăng giá', 'tốt nhất', 'top'])

            # Get ticker list from database
            ticker_list = self.db.search_stocks_by_criteria({'rsi_below': 100, 'limit': 100})

            if not ticker_list or len(ticker_list) == 0:
                return "❌ Không tìm thấy cổ phiếu nào."

            # Get full data for each ticker
            all_stocks = []
            for stock_dict in ticker_list[:50]:  # Limit to 50 to avoid timeout
                # ticker_list already contains stock data with ticker, close, rsi, etc.
                ticker = stock_dict.get('ticker') if isinstance(stock_dict, dict) else stock_dict
                if ticker:
                    data = self.db.get_latest_price(ticker)
                    if data:
                        all_stocks.append(data)

            if not all_stocks:
                return "❌ Không có dữ liệu cổ phiếu."

            # Calculate momentum if needed
            if is_momentum:
                stocks_with_momentum = []
                for stock in all_stocks:
                    ticker = stock.get('ticker')
                    # Get 7-day history for momentum
                    history = self.db.get_price_history(ticker, days=7)
                    if history and len(history) >= 2:
                        latest = history[0]['close']
                        oldest = history[-1]['close']
                        momentum = ((latest - oldest) / oldest) * 100
                        stock['momentum'] = momentum
                        stocks_with_momentum.append(stock)

                # Sort by momentum descending
                stocks_with_momentum.sort(key=lambda x: x.get('momentum', 0), reverse=True)
                stocks = stocks_with_momentum[:limit]

                response = f"🔍 **TOP {limit} CỔ PHIẾU CÓ MOMENTUM TỐT NHẤT**\n\n"
                response += "_Momentum = % tăng giá trong 7 ngày gần nhất_\n\n"

                for i, stock in enumerate(stocks, 1):
                    ticker = stock.get('ticker', 'N/A')
                    price = stock.get('close', 0)
                    momentum = stock.get('momentum', 0)
                    rsi = stock.get('rsi', 0)

                    emoji = "🚀" if momentum > 10 else "📈" if momentum > 5 else "🟢" if momentum > 0 else "📉"
                    response += f"{i}. **{ticker}**: {price:,.0f} VND | "
                    response += f"Momentum: **{momentum:+.2f}%** {emoji} | RSI: {rsi:.1f}\n"

            else:
                # Default: find undervalued stocks (RSI below 50)
                stocks = [s for s in all_stocks if s.get('rsi', 100) < 50][:limit]

                if not stocks:
                    return "❌ Không tìm thấy cổ phiếu phù hợp."

                response = f"🔍 **TÌM THẤY {len(stocks)} CỔ PHIẾU**\n\n"

                for i, stock in enumerate(stocks, 1):
                    ticker = stock.get('ticker', 'N/A')
                    price = stock.get('close', 0)
                    rsi = stock.get('rsi', 0)
                    response += f"{i}. **{ticker}**: {price:,.0f} VND | RSI: {rsi:.1f}"
                    if rsi < 30:
                        response += " 💡 (Quá bán)"
                    response += "\n"

            response += "\n💡 Dùng `@stock_bot phân tích <mã>` để xem chi tiết"

            return response

        except Exception as e:
            logger.error(f"Screener error: {e}", exc_info=True)
            return f"❌ Lỗi khi tìm kiếm: {str(e)}"

    async def handle_investment_query_llm(self, amount: int, query: str, tickers: list = None) -> str:
        """Investment advice (LLM version)"""
        try:
            # If specific tickers mentioned, use those
            if tickers and len(tickers) > 0:
                stocks = []
                for ticker in tickers:
                    data = self.db.get_latest_price(ticker)
                    if data:
                        stocks.append(data)

                if not stocks:
                    return f"❌ Không tìm thấy dữ liệu cho các mã: {', '.join(tickers)}"
            else:
                # No specific tickers, find good stocks
                stocks = self.db.search_stocks_by_criteria({'rsi_below': 50, 'limit': 5})

                if not stocks or len(stocks) < 3:
                    return "❌ Không đủ dữ liệu để tư vấn."

            if self.ai_client:
                context = f"Nhà đầu tư có {amount/1_000_000:.0f} triệu VND.\n\n"

                if tickers and len(tickers) > 0:
                    context += f"Người dùng muốn đầu tư vào các cổ phiếu: {', '.join(tickers)}\n\n"
                    context += "Dữ liệu cổ phiếu:\n"
                else:
                    context += "Các cổ phiếu tiềm năng:\n"

                for stock in stocks[:5]:
                    ticker = stock.get('ticker')
                    price = stock.get('close', 0)
                    rsi = stock.get('rsi', 0)
                    ma20 = stock.get('ma20', 0)
                    context += f"- {ticker}: Giá {price:,.0f} VND, RSI: {rsi:.1f}, MA20: {ma20:,.0f}\n"

                if tickers and len(tickers) > 0:
                    prompt = f"""{context}

Hãy phân bổ {amount/1_000_000:.0f} triệu VND vào các cổ phiếu này (250 từ):
1. Phân bổ vốn cụ thể cho TỪNG cổ phiếu (bao nhiêu % cho mỗi mã)
2. Tính số lượng cổ phiếu có thể mua
3. Lý do phân bổ như vậy (dựa vào RSI, giá, MA20)
4. Rủi ro cần lưu ý

Trả lời bằng tiếng Việt, chuyên nghiệp."""
                else:
                    prompt = f"""{context}

Hãy đưa ra lời khuyên đầu tư chi tiết (250 từ):
1. Chọn 2-3 cổ phiếu phù hợp
2. Phân bổ vốn cụ thể
3. Lý do đầu tư
4. Rủi ro cần lưu ý

Trả lời bằng tiếng Việt, chuyên nghiệp."""

                completion = self.ai_client.chat.completions.create(
                    model=self.ai_model,
                    messages=[
                        {"role": "system", "content": "Bạn là chuyên gia tư vấn đầu tư chứng khoán Việt Nam."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=600,
                    temperature=0.7
                )

                response = f"💰 **TƯ VẤN ĐẦU TƯ CHO {amount/1_000_000:.0f} TRIỆU VND**\n\n"
                response += completion.choices[0].message.content
                return response

            return "❌ Tính năng tư vấn AI chưa sẵn sàng."

        except Exception as e:
            return f"❌ Lỗi khi tư vấn: {str(e)}"

    async def handle_compare_query_llm(self, tickers: list) -> str:
        """Compare multiple stocks (LLM version)"""
        try:
            # Get data for all tickers
            stocks_data = []
            missing = []

            for ticker in tickers[:5]:  # Limit to 5 stocks max
                data = self.db.get_latest_price(ticker)
                if data:
                    # Get history for performance calculation
                    history = self.db.get_price_history(ticker, days=90)  # Last quarter
                    data['history'] = history
                    stocks_data.append(data)
                else:
                    missing.append(ticker)

            if missing:
                return f"❌ Không tìm thấy dữ liệu: {', '.join(missing)}"

            if len(stocks_data) < 2:
                return "❌ Cần ít nhất 2 cổ phiếu để so sánh."

            # Build comparison response
            ticker_names = [s['ticker'] for s in stocks_data]
            response = f"⚖️ **SO SÁNH {' vs '.join(ticker_names)}**\n\n"

            # Price comparison
            response += "**💰 Giá hiện tại:**\n"
            for stock in stocks_data:
                response += f"• {stock['ticker']}: {stock['close']:,.0f} VND"
                if stock.get('change_percent'):
                    change = stock['change_percent']
                    emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
                    response += f" ({change:+.2f}% {emoji})"
                response += "\n"

            # RSI comparison
            response += "\n**📊 RSI (Chỉ số sức mạnh tương đối):**\n"
            for stock in stocks_data:
                rsi = stock.get('rsi', 0)
                response += f"• {stock['ticker']}: {rsi:.1f}"
                if rsi < 30:
                    response += " 💡 (Quá bán - cơ hội)"
                elif rsi > 70:
                    response += " ⚠️ (Quá mua)"
                response += "\n"

            # Performance over last 90 days (quarter)
            response += "\n**📈 Hiệu suất 90 ngày (Quý vừa rồi):**\n"
            performances = []
            for stock in stocks_data:
                history = stock.get('history', [])
                if history and len(history) >= 2:
                    latest_price = history[0]['close']
                    oldest_price = history[-1]['close']
                    perf = ((latest_price - oldest_price) / oldest_price) * 100
                    performances.append((stock['ticker'], perf))
                    emoji = "📈" if perf > 0 else "📉"
                    response += f"• {stock['ticker']}: {perf:+.2f}% {emoji}\n"
                else:
                    response += f"• {stock['ticker']}: N/A (Không đủ dữ liệu)\n"

            # Find best performer
            if performances:
                best = max(performances, key=lambda x: x[1])
                worst = min(performances, key=lambda x: x[1])
                response += f"\n**🏆 Tốt nhất:** {best[0]} ({best[1]:+.2f}%)\n"
                response += f"**📉 Kém nhất:** {worst[0]} ({worst[1]:+.2f}%)\n"

            # Technical indicators comparison
            response += "\n**🔍 Xu hướng kỹ thuật:**\n"
            for stock in stocks_data:
                ticker = stock['ticker']
                close = stock.get('close', 0)
                ma20 = stock.get('ma20', 0)
                macd = stock.get('macd', 0)

                if close > ma20:
                    trend = "Tăng 📈"
                else:
                    trend = "Giảm 📉"

                response += f"• {ticker}: {trend}"
                if macd:
                    response += f", MACD: {macd:.2f}"
                response += "\n"

            response += "\n_💡 Tip: Dùng `@stock_bot phân tích <mã>` để xem chi tiết từng cổ phiếu_"

            return response

        except Exception as e:
            logger.error(f"Compare query error: {e}", exc_info=True)
            return f"❌ Lỗi khi so sánh: {str(e)}"

    async def handle_chart_request(self, ticker: str, days: int = 30) -> str:
        """Handle chart visualization requests"""
        try:
            # Check if stock exists
            price_data = self.db.get_latest_price(ticker)
            if not price_data:
                return f"❌ Không tìm thấy dữ liệu cho {ticker}"

            # Build response with chart link
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
            chart_url = f"{frontend_url}/stock/{ticker}"

            response = f"📊 **BIỂU ĐỒ {ticker}**\n\n"
            response += f"💰 Giá hiện tại: {price_data.get('close', 0):,.0f} VND\n"

            if price_data.get('change_percent'):
                change = price_data['change_percent']
                emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
                response += f"{emoji} Thay đổi: {change:+.2f}%\n"

            response += f"\n🔗 **Xem biểu đồ chi tiết ({days} ngày):**\n"
            response += f"{chart_url}\n\n"

            response += "**Biểu đồ bao gồm:**\n"
            response += "• 📈 Biểu đồ giá (Candlestick)\n"
            response += "• 📊 Chỉ báo RSI\n"
            response += "• 📉 MACD\n"
            response += "• 🎯 Bollinger Bands\n"
            response += "• 📏 Moving Averages (MA5, MA20)\n"

            response += f"\n💡 _Tip: Click vào link để xem biểu đồ tương tác với đầy đủ chỉ báo kỹ thuật_"

            return response

        except Exception as e:
            logger.error(f"Chart request error: {e}", exc_info=True)
            return f"❌ Lỗi khi tạo biểu đồ cho {ticker}: {str(e)}"

    async def handle_create_alert(self, user_id: int, ticker: str, condition: str, price: float) -> str:
        """Create price alert for user"""
        try:
            # Validate ticker exists
            price_data = self.db.get_latest_price(ticker)
            if not price_data:
                return f"❌ Không tìm thấy cổ phiếu {ticker}"

            # Create alert in database
            success = self.db.create_alert(
                user_id=str(user_id),
                ticker=ticker,
                alert_type="price",
                condition=condition,
                value=price
            )

            if success:
                current_price = price_data.get('close', 0)
                response = f"✅ **ĐÃ TẠO CẢNH BÁO**\n\n"
                response += f"📊 Cổ phiếu: **{ticker}**\n"
                response += f"💰 Giá hiện tại: {current_price:,.0f} VND\n"
                response += f"🎯 Điều kiện: Giá {condition} {price:,.0f} VND\n\n"
                response += "🔔 Bạn sẽ nhận được thông báo khi điều kiện được thỏa mãn.\n"
                response += "💡 _Dùng lệnh 'xem cảnh báo' để xem tất cả cảnh báo của bạn._"
                return response
            else:
                return "❌ Không thể tạo cảnh báo. Vui lòng thử lại sau."

        except Exception as e:
            logger.error(f"Create alert error: {e}", exc_info=True)
            return f"❌ Lỗi khi tạo cảnh báo: {str(e)}"

    async def handle_list_alerts(self, user_id: int) -> str:
        """List all active alerts for user"""
        try:
            alerts = self.db.get_user_alerts(str(user_id), active_only=True)

            if not alerts or len(alerts) == 0:
                return "📋 **DANH SÁCH CẢNH BÁO**\n\n🔕 Bạn chưa có cảnh báo nào.\n\n💡 _Tạo cảnh báo bằng cách: '@bot cảnh báo khi VIC lên 100000'_"

            response = f"📋 **DANH SÁCH CẢNH BÁO ({len(alerts)})**\n\n"

            for i, alert in enumerate(alerts, 1):
                ticker = alert.get('ticker', 'N/A')
                condition = alert.get('condition', '>')
                value = alert.get('value', 0)
                alert_id = alert.get('id', i)
                created = alert.get('created_at', '')

                # Get current price for comparison
                price_data = self.db.get_latest_price(ticker)
                current_price = price_data.get('close', 0) if price_data else 0

                response += f"{i}. **{ticker}** (ID: {alert_id})\n"
                response += f"   🎯 Điều kiện: Giá {condition} {value:,.0f} VND\n"
                response += f"   💰 Giá hiện tại: {current_price:,.0f} VND\n"
                if created:
                    response += f"   📅 Tạo: {created}\n"
                response += "\n"

            response += "💡 _Xóa cảnh báo: '@bot xóa cảnh báo số [ID]'_"
            return response

        except Exception as e:
            logger.error(f"List alerts error: {e}", exc_info=True)
            return f"❌ Lỗi khi lấy danh sách cảnh báo: {str(e)}"

    async def handle_delete_alert(self, user_id: int, alert_id: int) -> str:
        """Delete a specific alert"""
        try:
            # Get user's alerts to verify ownership
            alerts = self.db.get_user_alerts(str(user_id), active_only=True)

            if not alerts:
                return "❌ Bạn không có cảnh báo nào."

            # Find alert by position or ID
            target_alert = None
            for i, alert in enumerate(alerts, 1):
                if i == alert_id or alert.get('id') == alert_id:
                    target_alert = alert
                    break

            if not target_alert:
                return f"❌ Không tìm thấy cảnh báo số {alert_id}.\n\n💡 _Dùng 'xem cảnh báo' để xem danh sách._"

            # Delete alert
            db_alert_id = target_alert.get('id')
            if not db_alert_id:
                return "❌ Không thể xác định ID cảnh báo."

            success = self.db.delete_alert(int(db_alert_id))

            if success:
                ticker = target_alert.get('ticker', 'N/A')
                condition = target_alert.get('condition', '>')
                value = target_alert.get('value', 0)

                response = f"✅ **ĐÃ XÓA CẢNH BÁO**\n\n"
                response += f"📊 Cổ phiếu: **{ticker}**\n"
                response += f"🎯 Điều kiện: Giá {condition} {value:,.0f} VND\n\n"
                response += "💡 _Cảnh báo đã được xóa khỏi hệ thống._"
                return response
            else:
                return "❌ Không thể xóa cảnh báo. Vui lòng thử lại."

        except Exception as e:
            logger.error(f"Delete alert error: {e}", exc_info=True)
            return f"❌ Lỗi khi xóa cảnh báo: {str(e)}"

    async def handle_candlestick_analysis(self, ticker: str, days: int = 7) -> str:
        """Analyze candlestick patterns"""
        try:
            # Get price history with OHLC data
            history = self.db.get_price_history(ticker, days=days)

            if not history or len(history) < 3:
                return f"❌ Không đủ dữ liệu để phân tích nến Nhật cho {ticker}"

            response = f"🕯️ **PHÂN TÍCH NẾN NHẬT {ticker}**\n"
            response += f"📅 Phân tích {days} ngày gần nhất\n\n"

            # Detect candlestick patterns
            patterns_found = []
            signals = {"bullish": 0, "bearish": 0}

            for i in range(len(history) - 1):
                candle = history[i]
                prev_candle = history[i + 1] if i + 1 < len(history) else None

                open_price = candle.get('open', candle.get('close', 0))
                close_price = candle.get('close', 0)
                high_price = candle.get('high', close_price)
                low_price = candle.get('low', close_price)

                # Calculate candle properties
                body = abs(close_price - open_price)
                upper_shadow = high_price - max(open_price, close_price)
                lower_shadow = min(open_price, close_price) - low_price
                candle_range = high_price - low_price

                is_bullish = close_price > open_price
                is_bearish = close_price < open_price

                # Skip if no range
                if candle_range == 0:
                    continue

                day_label = f"Ngày {i+1}"

                # 1. DOJI - Body rất nhỏ (< 5% range)
                if body / candle_range < 0.05:
                    patterns_found.append(f"• **Doji** ({day_label}) - Tín hiệu đảo chiều, thị trường không chắc chắn ⚖️")

                # 2. HAMMER - Lower shadow dài, body nhỏ ở trên
                elif lower_shadow > body * 2 and upper_shadow < body * 0.3:
                    if is_bullish:
                        patterns_found.append(f"• **Hammer Tăng** ({day_label}) - Tín hiệu đảo chiều tăng mạnh 🔨📈")
                        signals["bullish"] += 2
                    else:
                        patterns_found.append(f"• **Hammer** ({day_label}) - Có thể đảo chiều tăng 🔨")
                        signals["bullish"] += 1

                # 3. INVERTED HAMMER - Upper shadow dài, body nhỏ ở dưới
                elif upper_shadow > body * 2 and lower_shadow < body * 0.3:
                    if is_bullish:
                        patterns_found.append(f"• **Inverted Hammer Tăng** ({day_label}) - Có thể đảo chiều tăng 🔨")
                        signals["bullish"] += 1
                    else:
                        patterns_found.append(f"• **Shooting Star** ({day_label}) - Tín hiệu giảm mạnh ⭐📉")
                        signals["bearish"] += 2

                # 4. MARUBOZU - Body dài, không có shadow (< 5% body)
                elif upper_shadow < body * 0.05 and lower_shadow < body * 0.05:
                    if is_bullish:
                        patterns_found.append(f"• **Marubozu Tăng** ({day_label}) - Xu hướng tăng rất mạnh 💪📈")
                        signals["bullish"] += 2
                    else:
                        patterns_found.append(f"• **Marubozu Giảm** ({day_label}) - Xu hướng giảm rất mạnh 💪📉")
                        signals["bearish"] += 2

                # 5. SPINNING TOP - Body nhỏ, cả hai shadow dài
                elif body / candle_range < 0.3 and upper_shadow > body and lower_shadow > body:
                    patterns_found.append(f"• **Spinning Top** ({day_label}) - Thị trường phân vân 🌀")

                # 6. LONG LEGGED DOJI - Doji với shadow rất dài
                elif body / candle_range < 0.05 and (upper_shadow > body * 3 or lower_shadow > body * 3):
                    patterns_found.append(f"• **Long Legged Doji** ({day_label}) - Sự phân vân cao 🎯")

                # 7. ENGULFING PATTERN - So sánh với nến trước
                if prev_candle and i < len(history) - 1:
                    prev_open = prev_candle.get('open', prev_candle.get('close', 0))
                    prev_close = prev_candle.get('close', 0)
                    prev_is_bullish = prev_close > prev_open

                    # Bullish Engulfing
                    if is_bullish and not prev_is_bullish:
                        if close_price > prev_open and open_price < prev_close:
                            patterns_found.append(f"• **Bullish Engulfing** ({day_label}) - Tín hiệu mua mạnh 🟢📈")
                            signals["bullish"] += 3

                    # Bearish Engulfing
                    if is_bearish and prev_is_bullish:
                        if open_price > prev_close and close_price < prev_open:
                            patterns_found.append(f"• **Bearish Engulfing** ({day_label}) - Tín hiệu bán mạnh 🔴📉")
                            signals["bearish"] += 3

            # Display patterns found
            if patterns_found:
                response += "**🔍 CÁC MẪU HÌNH NẾN PHÁT HIỆN:**\n"
                # Limit to most recent 10 patterns
                for pattern in patterns_found[:10]:
                    response += f"{pattern}\n"
                response += "\n"
            else:
                response += "**🔍 Không phát hiện mẫu hình nến đặc biệt.**\n\n"

            # Overall signal analysis
            response += "**💡 TỔNG KẾT TÍN HIỆU:**\n"
            total_signals = signals["bullish"] + signals["bearish"]

            if total_signals == 0:
                response += "⚪ **TRUNG LẬP** - Không có tín hiệu rõ ràng\n"
            elif signals["bullish"] > signals["bearish"] * 1.5:
                response += f"🟢 **TÍN HIỆU MUA MẠNH** - {signals['bullish']} tín hiệu tăng\n"
                response += "Các mẫu hình cho thấy xu hướng tăng có thể tiếp diễn.\n"
            elif signals["bullish"] > signals["bearish"]:
                response += f"📈 **Xu hướng Tăng** - {signals['bullish']} tín hiệu tăng, {signals['bearish']} tín hiệu giảm\n"
            elif signals["bearish"] > signals["bullish"] * 1.5:
                response += f"🔴 **TÍN HIỆU BÁN MẠNH** - {signals['bearish']} tín hiệu giảm\n"
                response += "Các mẫu hình cho thấy xu hướng giảm có thể tiếp diễn.\n"
            elif signals["bearish"] > signals["bullish"]:
                response += f"📉 **Xu hướng Giảm** - {signals['bearish']} tín hiệu giảm, {signals['bullish']} tín hiệu tăng\n"
            else:
                response += f"⚖️ **CÂN BẰNG** - {signals['bullish']} tín hiệu tăng, {signals['bearish']} tín hiệu giảm\n"

            # Get current price
            latest = history[0]
            current_price = latest.get('close', 0)
            response += f"\n💰 **Giá hiện tại**: {current_price:,.0f} VND\n"

            response += "\n_⚠️ Phân tích nến Nhật chỉ mang tính tham khảo. Cần kết hợp với các chỉ báo khác._"

            return response

        except Exception as e:
            logger.error(f"Candlestick analysis error: {e}", exc_info=True)
            return f"❌ Lỗi khi phân tích nến Nhật cho {ticker}: {str(e)}"

    async def handle_portfolio_analysis(self, holdings: list) -> str:
        """Analyze portfolio risk and performance"""
        try:
            if not holdings or len(holdings) == 0:
                return "❌ Danh mục trống. Vui lòng cung cấp ít nhất một cổ phiếu."

            response = f"📊 **PHÂN TÍCH DANH MỤC ĐẦU TƯ**\n\n"

            # Get data for all holdings
            portfolio_data = []
            total_value = 0
            missing_stocks = []

            for holding in holdings:
                ticker = holding.get('ticker', '').upper()
                quantity = holding.get('quantity', 0)

                if not ticker or quantity <= 0:
                    continue

                price_data = self.db.get_latest_price(ticker)
                if not price_data:
                    missing_stocks.append(ticker)
                    continue

                current_price = price_data.get('close', 0)
                value = current_price * quantity

                portfolio_data.append({
                    'ticker': ticker,
                    'quantity': quantity,
                    'price': current_price,
                    'value': value,
                    'rsi': price_data.get('rsi', 0),
                    'ma20': price_data.get('ma20', 0)
                })

                total_value += value

            if missing_stocks:
                response += f"⚠️ Không tìm thấy: {', '.join(missing_stocks)}\n\n"

            if not portfolio_data:
                return "❌ Không thể lấy dữ liệu cho danh mục của bạn."

            # Sort by value descending
            portfolio_data.sort(key=lambda x: x['value'], reverse=True)

            # Portfolio composition
            response += f"**💼 TỔNG QUAN DANH MỤC:**\n"
            response += f"💰 Tổng giá trị: **{total_value:,.0f} VND**\n"
            response += f"📈 Số lượng cổ phiếu: {len(portfolio_data)}\n\n"

            # Individual holdings
            response += "**📋 CHI TIẾT NẮM GIỮ:**\n"
            for i, stock in enumerate(portfolio_data, 1):
                ticker = stock['ticker']
                quantity = stock['quantity']
                price = stock['price']
                value = stock['value']
                allocation = (value / total_value) * 100

                response += f"{i}. **{ticker}**: {quantity} cổ @ {price:,.0f} VND\n"
                response += f"   💰 Giá trị: {value:,.0f} VND ({allocation:.1f}%)\n"

            # Diversification analysis
            response += "\n**🎯 PHÂN BỔ DANH MỤC:**\n"

            # Find concentration risk
            max_allocation = max([(s['value'] / total_value) * 100 for s in portfolio_data])
            top_3_allocation = sum([(s['value'] / total_value) * 100 for s in portfolio_data[:3]])

            if max_allocation > 40:
                response += f"⚠️ **RỦI RO TẬP TRUNG CAO**: Cổ phiếu lớn nhất chiếm {max_allocation:.1f}%\n"
                response += "   → Nên giảm tỷ trọng hoặc đa dạng hóa thêm\n"
            elif max_allocation > 25:
                response += f"⚡ **Tập trung vừa phải**: Cổ phiếu lớn nhất chiếm {max_allocation:.1f}%\n"
            else:
                response += f"✅ **Phân bổ tốt**: Không có cổ phiếu chiếm quá nhiều ({max_allocation:.1f}%)\n"

            response += f"📊 Top 3 chiếm: {top_3_allocation:.1f}% danh mục\n"

            # Số lượng cổ phiếu
            num_stocks = len(portfolio_data)
            if num_stocks < 3:
                response += f"\n⚠️ **Đa dạng hóa thấp**: Chỉ có {num_stocks} cổ phiếu\n"
                response += "   → Nên tăng lên ít nhất 5-10 cổ phiếu để giảm rủi ro\n"
            elif num_stocks < 5:
                response += f"\n⚡ **Đa dạng hóa khá**: {num_stocks} cổ phiếu\n"
            else:
                response += f"\n✅ **Đa dạng hóa tốt**: {num_stocks} cổ phiếu\n"

            # Technical analysis of portfolio
            response += "\n**📊 PHÂN TÍCH KỸ THUẬT:**\n"

            stocks_above_ma20 = sum(1 for s in portfolio_data if s['price'] > s['ma20'])
            stocks_oversold = sum(1 for s in portfolio_data if s['rsi'] < 30)
            stocks_overbought = sum(1 for s in portfolio_data if s['rsi'] > 70)

            pct_above_ma20 = (stocks_above_ma20 / num_stocks) * 100

            if pct_above_ma20 >= 70:
                response += f"📈 **Xu hướng mạnh**: {stocks_above_ma20}/{num_stocks} cổ phiếu trên MA20 ({pct_above_ma20:.0f}%)\n"
            elif pct_above_ma20 >= 40:
                response += f"⚖️ **Xu hướng trung bình**: {stocks_above_ma20}/{num_stocks} cổ phiếu trên MA20 ({pct_above_ma20:.0f}%)\n"
            else:
                response += f"📉 **Xu hướng yếu**: Chỉ {stocks_above_ma20}/{num_stocks} cổ phiếu trên MA20 ({pct_above_ma20:.0f}%)\n"

            if stocks_oversold > 0:
                oversold_tickers = [s['ticker'] for s in portfolio_data if s['rsi'] < 30]
                response += f"💡 **Quá bán** ({stocks_oversold}): {', '.join(oversold_tickers)} - Cơ hội mua thêm\n"

            if stocks_overbought > 0:
                overbought_tickers = [s['ticker'] for s in portfolio_data if s['rsi'] > 70]
                response += f"⚠️ **Quá mua** ({stocks_overbought}): {', '.join(overbought_tickers)} - Cân nhắc chốt lời\n"

            # Risk assessment
            response += "\n**⚠️ ĐÁNH GIÁ RỦI RO:**\n"

            risk_score = 0
            risk_factors = []

            # Concentration risk
            if max_allocation > 40:
                risk_score += 3
                risk_factors.append("Tập trung cao vào 1 cổ phiếu")
            elif max_allocation > 30:
                risk_score += 2

            # Diversification risk
            if num_stocks < 3:
                risk_score += 3
                risk_factors.append("Quá ít cổ phiếu (< 3)")
            elif num_stocks < 5:
                risk_score += 1

            # Technical weakness
            if pct_above_ma20 < 30:
                risk_score += 2
                risk_factors.append("Nhiều cổ phiếu trong xu hướng giảm")

            # Overbought risk
            if stocks_overbought >= num_stocks / 2:
                risk_score += 2
                risk_factors.append("Nhiều cổ phiếu quá mua")

            # Display risk level
            if risk_score >= 7:
                response += "🔴 **RỦI RO CAO**\n"
            elif risk_score >= 4:
                response += "🟡 **RỦI RO TRUNG BÌNH**\n"
            else:
                response += "🟢 **RỦI RO THẤP**\n"

            if risk_factors:
                for factor in risk_factors:
                    response += f"   • {factor}\n"

            # Recommendations
            response += "\n**💡 KHUYẾN NGHỊ:**\n"

            if max_allocation > 30:
                response += "1. Giảm tỷ trọng cổ phiếu chiếm tỷ lệ cao nhất\n"

            if num_stocks < 5:
                response += f"2. Tăng đa dạng hóa lên {5 - num_stocks} cổ phiếu nữa\n"

            if stocks_overbought > 0:
                response += "3. Cân nhắc chốt lời một phần cổ phiếu quá mua\n"

            if stocks_oversold > 0:
                response += "4. Có thể mua thêm cổ phiếu đang quá bán nếu triển vọng tốt\n"

            if pct_above_ma20 < 50:
                response += "5. Theo dõi sát thị trường, nhiều cổ phiếu đang yếu\n"

            response += "\n_⚠️ Đây chỉ là phân tích kỹ thuật, không phải lời khuyên đầu tư._"

            return response

        except Exception as e:
            logger.error(f"Portfolio analysis error: {e}", exc_info=True)
            return f"❌ Lỗi khi phân tích danh mục: {str(e)}"

    async def handle_subscribe(self, user_id: int, ticker: str) -> str:
        """Subscribe to a stock for monitoring"""
        try:
            # Create subscription
            subscription_id = self.db.create_subscription(
                user_id=str(user_id),
                ticker=ticker
            )

            if subscription_id:
                response = f"[OK] **DA THEO DOI**\n\n"
                response += f"[STOCK] Co phieu: **{ticker}**\n"
                response += f"[INFO] Ban se nhan duoc thong bao cap nhat ve {ticker}\n\n"
                response += "[LIGHT] _Dung 'xem theo doi' de xem danh sach day du._"
                return response
            else:
                return f"[ERROR] Khong the theo doi {ticker}. Vui long thu lai."

        except Exception as e:
            logger.error(f"Subscribe error: {e}", exc_info=True)
            return f"[ERROR] Loi khi theo doi co phieu: {str(e)}"

    async def handle_list_subscriptions(self, user_id: int) -> str:
        """List all subscriptions for a user"""
        try:
            subscriptions = self.db.get_user_subscriptions(str(user_id), active_only=True)

            if not subscriptions:
                return "[INFO] Ban chua theo doi co phieu nao.\n\n[LIGHT] _Dung 'theo doi [MA_CP]' de bat dau theo doi._"

            response = f"[LIST] **DANH SACH THEO DOI**\n"
            response += f"[INFO] Ban dang theo doi {len(subscriptions)} co phieu\n\n"

            for i, sub in enumerate(subscriptions, 1):
                ticker = sub.get('ticker', 'N/A')
                created_at = sub.get('created_at', 'N/A')

                # Format date if available
                date_str = created_at
                if isinstance(created_at, str) and len(created_at) > 10:
                    date_str = created_at[:10]

                response += f"{i}. **{ticker}** - Tu {date_str}\n"

            response += "\n[LIGHT] _Dung 'huy theo doi [MA_CP]' de ngung theo doi._"
            return response

        except Exception as e:
            logger.error(f"List subscriptions error: {e}", exc_info=True)
            return f"[ERROR] Loi khi lay danh sach theo doi: {str(e)}"

    async def handle_unsubscribe(self, user_id: int, ticker: str) -> str:
        """Unsubscribe from a stock"""
        try:
            # Get user's subscriptions to verify
            subscriptions = self.db.get_user_subscriptions(str(user_id), active_only=True)

            if not subscriptions:
                return "[ERROR] Ban khong co theo doi nao."

            # Find the subscription
            target_sub = None
            for sub in subscriptions:
                if sub.get('ticker', '').upper() == ticker.upper():
                    target_sub = sub
                    break

            if not target_sub:
                return f"[ERROR] Ban khong theo doi {ticker}.\n\n[LIGHT] _Dung 'xem theo doi' de xem danh sach._"

            # Delete subscription
            sub_id = target_sub.get('id')
            if not sub_id:
                return "[ERROR] Khong the xac dinh ID theo doi."

            success = self.db.delete_subscription(int(sub_id))

            if success:
                response = f"[OK] **DA HUY THEO DOI**\n\n"
                response += f"[STOCK] Co phieu: **{ticker}**\n"
                response += f"[INFO] Ban se khong con nhan thong bao ve {ticker}\n\n"
                response += "[LIGHT] _Theo doi da duoc xoa khoi he thong._"
                return response
            else:
                return "[ERROR] Khong the huy theo doi. Vui long thu lai."

        except Exception as e:
            logger.error(f"Unsubscribe error: {e}", exc_info=True)
            return f"[ERROR] Loi khi huy theo doi: {str(e)}"

    async def handle_fundamentals_request(self, ticker: str, metrics: Optional[list] = None) -> str:
        """Handle fundamental metrics requests (P/E, EPS, ROE, etc.)"""
        try:
            # Get fundamental data from database
            ratios_data = self.db.get_financial_ratios([ticker])

            if not ratios_data or ticker not in ratios_data:
                return f"❌ **Xin lỗi, hiện tại chưa có dữ liệu chỉ số tài chính cho {ticker}.**\n\n💡 _Dữ liệu sẽ được cập nhật trong thời gian tới._"

            data = ratios_data[ticker]

            # If specific metrics requested, filter them
            available_metrics = {
                'PE': data.get('pe'),
                'P/E': data.get('pe'),
                'EPS': data.get('eps'),
                'ROE': data.get('roe'),
                'ROA': data.get('roa'),
                'PB': data.get('pb'),
                'P/B': data.get('pb'),
                'PS': data.get('ps'),
                'P/S': data.get('ps'),
                'Debt/Equity': data.get('debt_equity'),
                'Market Cap': data.get('market_capital'),
                'BVPS': data.get('bvps'),
                'Current Ratio': data.get('current_ratio'),
                'Quick Ratio': data.get('quick_ratio'),
                'Gross Margin': data.get('gross_profit_margin'),
                'Net Margin': data.get('net_profit_margin'),
                'EBITDA': data.get('ebitda'),
                'ROIC': data.get('roic'),
            }

            response = f"📊 **CHỈ SỐ TÀI CHÍNH {ticker}**\n"
            response += f"📅 Quý {data.get('quarter', 'N/A')}/{data.get('year', 'N/A')}\n\n"

            # If user specified metrics, show only those
            if metrics and len(metrics) > 0:
                requested_found = False
                for metric in metrics:
                    metric_upper = metric.upper().replace('_', ' ').strip()
                    value = None

                    # Find matching metric
                    for key, val in available_metrics.items():
                        if key.upper() == metric_upper:
                            value = val
                            break

                    if value is not None and value != 0:
                        requested_found = True
                        if 'RATIO' in metric_upper or metric_upper in ['PE', 'P/E', 'PB', 'P/B', 'PS', 'P/S', 'DEBT/EQUITY']:
                            response += f"• **{metric}**: {value:.2f}\n"
                        elif 'MARGIN' in metric_upper or metric_upper in ['ROE', 'ROA', 'ROIC']:
                            response += f"• **{metric}**: {value:.2f}%\n"
                        elif 'MARKET CAP' in metric_upper or 'EBITDA' in metric_upper:
                            response += f"• **{metric}**: {value:,.0f} tỷ VND\n"
                        else:
                            response += f"• **{metric}**: {value:,.2f}\n"
                    else:
                        response += f"• **{metric}**: _Không có dữ liệu_\n"

                if not requested_found:
                    return f"❌ **Xin lỗi, hiện tại chưa có dữ liệu về các chỉ số: {', '.join(metrics)} cho {ticker}.**"

            else:
                # Show all available key metrics
                response += "**📈 Định giá (Valuation):**\n"
                if data.get('pe'):
                    response += f"• P/E: {data['pe']:.2f}\n"
                else:
                    response += "• P/E: _Không có dữ liệu_\n"

                if data.get('pb'):
                    response += f"• P/B: {data['pb']:.2f}\n"
                else:
                    response += "• P/B: _Không có dữ liệu_\n"

                if data.get('ps'):
                    response += f"• P/S: {data['ps']:.2f}\n"
                else:
                    response += "• P/S: _Không có dữ liệu_\n"

                response += "\n**💰 Lợi nhuận (Profitability):**\n"
                if data.get('eps'):
                    response += f"• EPS: {data['eps']:,.0f} VND\n"
                else:
                    response += "• EPS: _Không có dữ liệu_\n"

                if data.get('roe'):
                    response += f"• ROE: {data['roe']:.2f}%\n"
                else:
                    response += "• ROE: _Không có dữ liệu_\n"

                if data.get('roa'):
                    response += f"• ROA: {data['roa']:.2f}%\n"
                else:
                    response += "• ROA: _Không có dữ liệu_\n"

                if data.get('net_profit_margin'):
                    response += f"• Net Margin: {data['net_profit_margin']:.2f}%\n"
                else:
                    response += "• Net Margin: _Không có dữ liệu_\n"

                response += "\n**🏦 Thanh khoản & Nợ (Liquidity & Debt):**\n"
                if data.get('current_ratio'):
                    response += f"• Current Ratio: {data['current_ratio']:.2f}\n"
                else:
                    response += "• Current Ratio: _Không có dữ liệu_\n"

                if data.get('quick_ratio'):
                    response += f"• Quick Ratio: {data['quick_ratio']:.2f}\n"
                else:
                    response += "• Quick Ratio: _Không có dữ liệu_\n"

                if data.get('debt_equity'):
                    response += f"• Debt/Equity: {data['debt_equity']:.2f}\n"
                else:
                    response += "• Debt/Equity: _Không có dữ liệu_\n"

                response += "\n**📊 Khác (Other):**\n"
                if data.get('market_capital'):
                    response += f"• Market Cap: {data['market_capital']:,.0f} tỷ VND\n"
                else:
                    response += "• Market Cap: _Không có dữ liệu_\n"

                if data.get('bvps'):
                    response += f"• BVPS: {data['bvps']:,.0f} VND\n"
                else:
                    response += "• BVPS: _Không có dữ liệu_\n"

            response += "\n💡 _Tip: Hỏi 'so sánh P/E của VCB và TCB' để so sánh các chỉ số_"

            return response

        except Exception as e:
            logger.error(f"Fundamentals request error: {e}", exc_info=True)
            return f"❌ Xin lỗi, không thể lấy dữ liệu chỉ số tài chính cho {ticker}: {str(e)}"

    async def handle_general_llm(self, query: str, user_id: int) -> str:
        """Handle general questions with LLM"""
        if not self.ai_client:
            return "🤖 Tính năng AI chưa sẵn sàng."

        try:
            history = self.conversations.get(user_id, [])
            messages = [
                {"role": "system", "content": "Bạn là chuyên gia chứng khoán Việt Nam. Trả lời ngắn gọn (150 từ), chuyên nghiệp bằng tiếng Việt."}
            ]

            for msg in history[-3:]:
                role = "assistant" if msg['role'] == "assistant" else "user"
                messages.append({"role": role, "content": msg['content']})

            messages.append({"role": "user", "content": query})

            completion = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=messages,
                max_tokens=400,
                temperature=0.7
            )

            response = completion.choices[0].message.content

            # Store in conversation
            self.conversations[user_id].append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now()
            })

            return response

        except Exception as e:
            return f"❌ Lỗi AI: {str(e)}"

    def split_message(self, text: str, max_length: int = 2000) -> list:
        """Split long message into chunks"""
        if len(text) <= max_length:
            return [text]

        chunks = []
        current = ""

        for line in text.split('\n'):
            if len(current) + len(line) + 1 <= max_length:
                current += line + '\n'
            else:
                if current:
                    chunks.append(current)
                current = line + '\n'

        if current:
            chunks.append(current)

        return chunks

    async def close(self):
        """Cleanup on shutdown"""
        logger.info("🛑 Shutting down bot...")
        self.db.close()
        await super().close()


# Create bot instance
bot = SimpleStockBot()


# ============================================================================
# MINIMAL COMMANDS (Backup only - chủ yếu dùng mention)
# ============================================================================

@bot.command(name="help", aliases=["huongdan", "hd"])
async def help_command(ctx):
    """Help command (backup)"""
    embed = discord.Embed(
        title="🤖 Stock Bot - Hướng dẫn",
        description="Bot phân tích chứng khoán Việt Nam với AI",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="✨ Cách sử dụng CHÍNH",
        value=(
            "**Chỉ cần mention bot:**\n"
            "`@stock_bot <câu hỏi>`\n\n"
            "Không cần nhớ lệnh phức tạp!"
        ),
        inline=False
    )

    embed.add_field(
        name="📝 Ví dụ",
        value=(
            "• `@stock_bot giá VCB`\n"
            "• `@stock_bot phân tích HPG`\n"
            "• `@stock_bot tìm cổ phiếu tốt`\n"
            "• `@stock_bot với 100 triệu nên đầu tư gì`\n"
            "• `@stock_bot so sánh VCB và ACB`\n"
            "• Bất kỳ câu hỏi nào về chứng khoán!"
        ),
        inline=False
    )

    embed.add_field(
        name="🎯 Bot tự động hiểu",
        value=(
            "✅ Giá cổ phiếu\n"
            "✅ Phân tích kỹ thuật\n"
            "✅ Tìm kiếm & lọc\n"
            "✅ Tư vấn đầu tư\n"
            "✅ So sánh cổ phiếu\n"
            "✅ Câu hỏi chung"
        ),
        inline=False
    )

    embed.set_footer(text="Powered by AI Hybrid System | Mention @stock_bot để bắt đầu!")

    await ctx.send(embed=embed)


@bot.command(name="stats", aliases=["thongke"])
async def stats_command(ctx):
    """Show bot statistics"""
    stats = bot.stats
    uptime = datetime.now() - stats["start_time"]

    embed = discord.Embed(
        title="📊 Thống kê Bot",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="📈 Truy vấn",
        value=(
            f"Tổng: {stats['total_queries']}\n"
            f"Giá: {stats['price_queries']}\n"
            f"Phân tích: {stats['analysis_queries']}\n"
            f"Tìm kiếm: {stats['screener_queries']}\n"
            f"Đầu tư: {stats['investment_queries']}\n"
            f"Khác: {stats['general_queries']}"
        ),
        inline=True
    )

    embed.add_field(
        name="⚡ Hiệu suất",
        value=(
            f"Lỗi: {stats['errors']}\n"
            f"Thành công: {stats['total_queries'] - stats['errors']}\n"
            f"Success rate: {((stats['total_queries'] - stats['errors']) / max(stats['total_queries'], 1) * 100):.1f}%"
        ),
        inline=True
    )

    embed.add_field(
        name="⏱️ Uptime",
        value=f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m",
        inline=True
    )

    # Database stats
    db_stats = bot.db.get_stats()
    embed.add_field(
        name="💾 Database",
        value=(
            f"Calls: {db_stats['total_calls']}\n"
            f"Cache hits: {db_stats['cache_hits']}\n"
            f"Hit rate: {db_stats['cache_hit_rate']}"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        # Silently ignore - user should use mention instead
        pass
    else:
        logger.error(f"Command error: {error}", exc_info=True)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run the bot"""
    token = os.getenv("DISCORD_BOT_TOKEN")

    if not token:
        logger.error("❌ DISCORD_BOT_TOKEN not found in .env")
        print("\n⚠️ Vui lòng thêm DISCORD_BOT_TOKEN vào file .env")
        print("   DISCORD_BOT_TOKEN=your_token_here\n")
        return

    try:
        logger.info("🚀 Starting Simple Stock Bot...")
        print("\n" + "="*60)
        print("🤖 SIMPLE STOCK BOT")
        print("="*60)
        print("✨ Chỉ cần mention @stock_bot <câu hỏi> để sử dụng!")
        print("📝 Ví dụ: @stock_bot giá VCB")
        print("="*60 + "\n")

        bot.run(token)
    except discord.LoginFailure:
        logger.error("❌ Invalid Discord token!")
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Error running bot: {e}", exc_info=True)
    finally:
        # Cleanup
        try:
            asyncio.run(bot.close())
        except:
            pass


if __name__ == "__main__":
    main()
