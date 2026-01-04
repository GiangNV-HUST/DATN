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

    async def handle_compare_query(self, query: str) -> str:
        """Handle stock comparison queries"""
        # Extract tickers
        tickers = re.findall(r'\b([A-Z]{3,4})\b', query.upper())

        if len(tickers) < 2:
            return (
                "🤔 Bạn muốn so sánh cổ phiếu nào?\n\n"
                "Ví dụ: `@stock_bot so sánh VCB và ACB`"
            )

        try:
            ticker1, ticker2 = tickers[0], tickers[1]

            # Get data for both
            data1 = self.db.get_latest_price(ticker1)
            data2 = self.db.get_latest_price(ticker2)

            if not data1 or not data2:
                return f"❌ Không tìm thấy dữ liệu cho một trong các mã: {ticker1}, {ticker2}"

            # Format comparison
            response = f"⚖️ **SO SÁNH {ticker1} vs {ticker2}**\n\n"

            # Price
            response += f"**💰 Giá:**\n"
            response += f"• {ticker1}: {data1['close']:,.0f} VND\n"
            response += f"• {ticker2}: {data2['close']:,.0f} VND\n"

            # RSI
            if data1.get('rsi') and data2.get('rsi'):
                response += f"\n**📊 RSI:**\n"
                response += f"• {ticker1}: {data1['rsi']:.1f}"
                response += " (Tốt hơn 💡)\n" if data1['rsi'] < data2['rsi'] else "\n"
                response += f"• {ticker2}: {data2['rsi']:.1f}"
                response += " (Tốt hơn 💡)\n" if data2['rsi'] < data1['rsi'] else "\n"

            # Change %
            if data1.get('change_percent') and data2.get('change_percent'):
                response += f"\n**📈 Thay đổi:**\n"
                response += f"• {ticker1}: {data1['change_percent']:+.2f}%\n"
                response += f"• {ticker2}: {data2['change_percent']:+.2f}%\n"

            response += "\n💡 Dùng `@stock_bot phân tích <mã>` để xem chi tiết từng cổ phiếu"

            return response

        except Exception as e:
            logger.error(f"Error in compare query: {e}")
            return f"❌ Lỗi khi so sánh: {str(e)}"

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
- Nếu người dùng hỏi về GIÁ: Trả về JSON {{"action": "get_price", "ticker": "MÃ_CP"}}
- Nếu người dùng muốn PHÂN TÍCH: Trả về JSON {{"action": "analyze", "ticker": "MÃ_CP"}}
- Nếu người dùng muốn TÌM KIẾM: Trả về JSON {{"action": "screener", "criteria": "mô tả tiêu chí"}}
- Nếu người dùng muốn TƯ VẤN ĐẦU TƯ:
  + Có đề cập cổ phiếu cụ thể (VD: "100 triệu vào FPT và HPG"): {{"action": "invest", "amount": số_tiền, "tickers": ["FPT", "HPG"]}}
  + Không đề cập cổ phiếu (VD: "100 triệu nên đầu tư gì"): {{"action": "invest", "amount": số_tiền}}
- Nếu người dùng muốn SO SÁNH: Trả về JSON {{"action": "compare", "tickers": ["MÃ1", "MÃ2"]}}
- Nếu là CÂU HỎI CHUNG: Trả về JSON {{"action": "general", "question": "câu hỏi"}}

LƯU Ý QUAN TRỌNG:
- Luôn trả về JSON hợp lệ
- Mã cổ phiếu phải viết HOA (VD: VCB, HPG, VNM, FPT)
- QUAN TRỌNG: Tìm TẤT CẢ các mã cổ phiếu trong câu hỏi (FPT, HPG, VCB, v.v.) và đưa vào mảng "tickers"
- Số tiền: 100 triệu = 100000000, 50 triệu = 50000000, 200 triệu = 200000000
- amount phải là số nguyên, tính bằng VND (không có dấu phẩy)"""

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

            elif action == 'compare':
                tickers = decision.get('tickers', [])
                if len(tickers) >= 2:
                    self.stats["general_queries"] += 1
                    return await self.handle_compare_query_llm(tickers[0], tickers[1])
                else:
                    return "🤔 Bạn muốn so sánh 2 cổ phiếu nào?"

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

            if price_data.get('rsi'):
                rsi = price_data['rsi']
                response += f"• **RSI**: {rsi:.1f}"
                if rsi > 70:
                    response += " ⚠️ QUÁ MUA - Cẩn thận\n"
                elif rsi < 30:
                    response += " 💡 QUÁ BÁN - Cơ hội mua\n"
                else:
                    response += " ✅ Ở mức trung bình\n"

            if price_data.get('ma20'):
                ma20 = price_data['ma20']
                close = price_data.get('close', 0)
                response += f"• **MA20**: {ma20:,.0f} VND"
                response += " 📈 Tích cực\n" if close > ma20 else " 📉 Tiêu cực\n"

            if price_data.get('macd'):
                macd = price_data['macd']
                response += f"• **MACD**: {macd:.2f}"
                response += " 🟢 Tích cực\n" if macd > 0 else " 🔴 Tiêu cực\n"

            if history and len(history) >= 5:
                response += "\n**📊 XU HƯỚNG GIÁ:**\n"
                recent = [h['close'] for h in history[:5]]
                if recent[0] > recent[-1]:
                    pct = ((recent[0] - recent[-1]) / recent[-1]) * 100
                    response += f"• 5 ngày: **Tăng** {pct:.1f}% 📈\n"
                else:
                    pct = ((recent[-1] - recent[0]) / recent[0]) * 100
                    response += f"• 5 ngày: **Giảm** {pct:.1f}% 📉\n"

            return response

        except Exception as e:
            return f"❌ Lỗi khi phân tích {ticker}: {str(e)}"

    async def handle_screener_query_llm(self, criteria_text: str) -> str:
        """Screen stocks (LLM version)"""
        try:
            # Use default criteria
            stocks = self.db.search_stocks_by_criteria({'rsi_below': 50, 'limit': 10})

            if not stocks or len(stocks) == 0:
                return "❌ Không tìm thấy cổ phiếu phù hợp."

            response = f"🔍 **TÌM THẤY {len(stocks)} CỔ PHIẾU**\n\n"

            for i, stock in enumerate(stocks[:10], 1):
                ticker = stock.get('ticker', 'N/A')
                price = stock.get('close', 0)
                rsi = stock.get('rsi', 0)
                response += f"{i}. **{ticker}**: {price:,.0f} VND | RSI: {rsi:.1f}"
                if rsi < 30:
                    response += " 💡"
                elif rsi > 70:
                    response += " ⚠️"
                response += "\n"

            return response

        except Exception as e:
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

    async def handle_compare_query_llm(self, ticker1: str, ticker2: str) -> str:
        """Compare two stocks (LLM version)"""
        try:
            data1 = self.db.get_latest_price(ticker1)
            data2 = self.db.get_latest_price(ticker2)

            if not data1 or not data2:
                missing = []
                if not data1: missing.append(ticker1)
                if not data2: missing.append(ticker2)
                return f"❌ Không tìm thấy: {', '.join(missing)}"

            response = f"⚖️ **SO SÁNH {ticker1} vs {ticker2}**\n\n"
            response += f"**💰 Giá:**\n"
            response += f"• {ticker1}: {data1['close']:,.0f} VND\n"
            response += f"• {ticker2}: {data2['close']:,.0f} VND\n"

            if data1.get('rsi') and data2.get('rsi'):
                response += f"\n**📊 RSI:**\n"
                response += f"• {ticker1}: {data1['rsi']:.1f}\n"
                response += f"• {ticker2}: {data2['rsi']:.1f}\n"

            return response

        except Exception as e:
            return f"❌ Lỗi khi so sánh: {str(e)}"

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
