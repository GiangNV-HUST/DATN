"""
OpenAI client for Streamlit UI.
This provides a simple chat interface using OpenAI instead of the complex agent system.
"""

import os
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Simple OpenAI client for chat interface.
    Alternative to the complex HybridOrchestrator when you want simpler setup.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (gpt-4o, gpt-4o-mini, gpt-3.5-turbo, etc.)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment or parameters")

        self.model = model
        self.client = AsyncOpenAI(api_key=self.api_key)

        # System prompt for stock advisor
        self.system_prompt = """Bạn là một trợ lý AI chuyên về tư vấn đầu tư chứng khoán thông minh.

Bạn có thể:
- Phân tích cổ phiếu (kỹ thuật, tài chính, tin tức)
- Tư vấn đầu tư và phân bổ danh mục
- Tìm kiếm cổ phiếu tiềm năng
- Giải thích các khái niệm tài chính
- Cung cấp thông tin về thị trường chứng khoán Việt Nam

Hãy trả lời một cách chuyên nghiệp, chi tiết và dễ hiểu. Sử dụng tiếng Việt.
Luôn cảnh báo về rủi ro đầu tư và khuyến nghị người dùng tự nghiên cứu kỹ.
"""

        logger.info(f"OpenAI client initialized with model: {model}")

    async def chat(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a chat message and get response.

        Args:
            user_message: User's message
            conversation_history: Previous conversation (list of {"role": "user/assistant", "content": "..."})
            temperature: Sampling temperature (0-2)
            max_tokens: Max tokens in response

        Returns:
            Dict with response and metadata
        """

        try:
            # Build messages
            messages = [{"role": "system", "content": self.system_prompt}]

            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history)

            # Add current message
            messages.append({"role": "user", "content": user_message})

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Extract response
            assistant_message = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            # Get usage stats
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0

            logger.info(
                f"OpenAI chat completed: {total_tokens} tokens "
                f"({prompt_tokens} prompt + {completion_tokens} completion)"
            )

            return {
                "response": assistant_message,
                "finish_reason": finish_reason,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                },
                "model": self.model
            }

        except Exception as e:
            logger.error(f"OpenAI chat error: {e}", exc_info=True)
            return {
                "response": f"Xin lỗi, đã có lỗi xảy ra: {str(e)}",
                "error": str(e),
                "model": self.model
            }

    async def chat_stream(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """
        Send a chat message and stream response.

        Args:
            user_message: User's message
            conversation_history: Previous conversation
            temperature: Sampling temperature
            max_tokens: Max tokens in response

        Yields:
            String chunks of the response
        """

        try:
            # Build messages
            messages = [{"role": "system", "content": self.system_prompt}]

            if conversation_history:
                messages.extend(conversation_history)

            messages.append({"role": "user", "content": user_message})

            # Call OpenAI streaming API
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            # Yield chunks
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}", exc_info=True)
            yield f"\n\n❌ Lỗi: {str(e)}"


# Singleton instance
_openai_client = None


def get_openai_client(api_key: Optional[str] = None, model: Optional[str] = None) -> OpenAIClient:
    """
    Get or create singleton OpenAI client.

    Args:
        api_key: OpenAI API key (optional, uses env var if not provided)
        model: Model name (optional, uses default if not provided)

    Returns:
        OpenAIClient instance
    """
    global _openai_client

    # Get model from env or use default
    if model is None:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Create new client if needed or if params changed
    if _openai_client is None or _openai_client.model != model:
        _openai_client = OpenAIClient(api_key=api_key, model=model)

    return _openai_client
