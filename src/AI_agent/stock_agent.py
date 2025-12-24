"""
Stock Analysis AI Agent
Agent thông minh để phân tích cổ phiếu
"""

import google.generativeai as genai
import json
import logging
from src.config import Config
from src.AI_agent.database_tools import DatabaseTools

logger = logging.getLogger(__name__)


class StockAnalysisAgent:
    """AI Agent phân tích cổ phiếu với Gemini"""

    def __init__(self):
        """Khởi tạo agent"""
        # Configure Gemini
        genai.configure(api_key=Config.GEMINI_API_KEY)

        # Model
        self.model = genai.GenerativeModel("gemini-2.5-flash-lite")

        # Database tools
        self.db_tools = DatabaseTools()

        # System prompt
        self.system_prompt = """
        Bạn là một chuyên gia phân tích chứng khoán Việt Nam
        Nhiệm vụ của bạn là giúp nhà đầu tư phân tích cổ phiếu và đưa ra insights.
        
        Khi phân tích cổ phiếu, hãy:
        1. Phân tích giá hiện tại và xu hướng
        2. Đánh giá các chỉ báo kĩ thuật (RSI, MA, MACD)
        3. So sánh với dự đoán (nếu có)
        4. Đưa ra nhận xét và khuyến nghị (MUA/BÁN/GIỮ)
        
        Format câu trả lời rõ ràng, dễ hiểu, có emoji để dễ đọc.
        """

        logger.info("✅ Stock Analysis Agent initialized")

    def analyze_stock(self, ticker):
        """
        Phân tích toàn diện 1 cổ phiếu

        Args:
            ticker: Mã cổ phiếu

        Returns:
            str: Phân tích chi tiết
        """
        try:
            # 1. Lấy dữ liệu từ database
            latest_price = self.db_tools.get_latest_price(ticker)
            predictions = self.db_tools.get_predictions(ticker)
            history = self.db_tools.get_price_history(ticker, days=10)

            if not latest_price:
                return f"❌ Không tìm thấy dữ liệu cho {ticker}"

            # 2. Chuẩn bị context cho AI
            context = self._prepare_context(ticker, latest_price, predictions, history)

            # 3. Gọi Gemini để phân tích
            prompt = f"{self.system_prompt}\n\n{context}\n\nHãy phân tích cổ phiếu này."

            response = self.model.generate_content(prompt)

            return response.text

        except Exception as e:
            logger.error(f"Error analyzing stock {ticker}: {e}")
            # Raise exception để Discord bot có thể catch và gửi message lỗi
            raise Exception(f"Không thể phân tích {ticker}: {str(e)}")

    def answer_question(self, question):
        """
        Trả lời câu hỏi về cổ phiếu

        Args:
            question: Câu hỏi của user

        Returns:
            str: Câu trả lời
        """
        try:
            # Detect ticker trong câu hỏi
            ticker = self._extract_ticker(question)

            if ticker:
                # Lấy data
                latest_price = self.db_tools.get_latest_price(ticker)

                if latest_price:
                    context = self._prepare_context(ticker, latest_price, None, [])
                    prompt = f"{self.system_prompt}\n\n{context}\n\nCâu hỏi: {question}"
                else:
                    prompt = f"{self.system_prompt}\n\nCâu hỏi: {question}\n\n(Không tìm thấy dữ liệu cho {ticker})"
            else:
                prompt = f"{self.system_prompt}\n\nCâu hỏi: {question}"

            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Error answering question: {e}")
            # Raise exception để Discord bot có thể catch và gửi message lỗi
            raise Exception(f"Không thể trả lời câu hỏi: {str(e)}")

    def find_opportunities(self, criteria_text):
        """
        Tìm kiếm cơ hội đầu tư theo tiêu chí

        Args:
            str: Danh sách cổ phiếu phù hợp
        """
        try:
            # Pause Criteria
            criteria = self._parse_criteria(criteria_text)

            # Search database
            stocks = self.db_tools.search_stocks_by_criteria(criteria)

            if not stocks:
                return "❌ Không tìm thấy cổ phiếu nào phù hợp"

            # Format results
            result = f"📊 Tìm thấy {len(stocks)} cổ phiếu: \n\n"
            for stock in stocks[:10]:
                result += f". **{stock['ticker']}**: {stock['close']:,.0f}đ"
                if stock["rsi"]:
                    result += f" | RSI: {stock['rsi']:.1f}"
                result += "\n"

            return result
        except Exception as e:
            logger.error(f"Error finding opportunities: {e}")
            return f"❌ Lỗi: {str(e)}"

    def _prepare_context(self, ticker, latest, predictions, history):
        """Chuẩn bị context cho AI"""
        context = f"Phân tích cổ phiếu {ticker}:\n\n"

        # Current price
        context += f"📊 Giá hiện tại ({latest['time']}):\n"
        context += f"   - Đóng cửa: {latest['close']:,.0f}đ\n"
        context += f"   - Mở cửa: {latest['open']:,.0f}đ\n"
        context += f"   - Cao nhất: {latest['high']:,.0f}đ\n"
        context += f"   - Thấp nhất: {latest['low']:,.0f}đ\n"
        context += f"   - Khối lượng: {latest['volume']:,.0f}đ\n"

        # Indicators
        if latest["ma5"] and latest["ma20"]:
            context += f"📈 Chỉ báo kĩ thuật:\n"
            if latest["ma5"]:
                context += f"   - MA5: {latest['ma5']:,.0f}đ\n"
            if latest["ma20"]:
                context += f"   - MA20: {latest['ma20']:,.0f}đ\n"
            if latest["rsi"]:
                context += f"   - RSI: {latest['rsi']:.1f}đ\n"
            if latest["macd"]:
                context += f"   -MACD: {latest['macd']:.2f}đ\n"
            context += "\n"

        # Predictions
        if predictions:
            context += f"🔮 Dự đoán 3 ngày tới:\n"
            context += f"   - Ngày 1: {predictions['day1']:,.0f}đ\n"
            context += f"   - Ngày 2: {predictions['day2']:,.0f}đ\n"
            context += f"   - Ngày 3: {predictions['day3']:,.0f}đ\n\n"

        # History trend
        if len(history) >= 5:
            context += f"📉 Xu hướng 5 ngày gần nhất:\n"
            for h in history[:5]:
                context += f"   - {h['time']}: {h['close']:,.0f}đ\n"

        return context

    def _extract_ticker(self, text):
        """Trích xuất mã cổ phiếu từ text"""
        import re
        # Tìm pattern: 3-4 chữ cái viết hoa
        match= re.search(r"\b[A-Z]{3,4}\b",text.upper())
        return match.group(0) if match else None
    
    def _parse_criteria(self, text):
        """Parse tiêu chí tìm kiếm"""
        criteria = {}
        
        text_lower = text.lower()
        
        # RSI
        if "rsi" in text_lower:
            if "dưới" in text_lower or "nhỏ hơn" in text_lower or "<" in text_lower:
                import re
                match = re.search(r"(\d+)",text)
                if match:
                    criteria['rsi_below'] = int(match.group(1))
            
            elif "trên" in text_lower or "lớn hơn" in text_lower or ">" in text_lower:
                import re 
                match = re.search(r"(\d+)", text)
                if match:
                    criteria['rsi_above'] = int(match.group(1))
                    
            return criteria if criteria else {'rsi_below': 30} # Default
        
    def __del__(self):
        """Cleanup"""
        if hasattr(self, "db_tools"):
            self.db_tools.close() 
