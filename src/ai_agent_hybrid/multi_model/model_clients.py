"""
Multi-Model Clients
Unified interface cho các AI models: Gemini, Claude, GPT-4
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import os
import json
from dataclasses import dataclass


@dataclass
class ModelResponse:
    """Standardized response từ models"""
    content: str
    model: str
    task_type: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = None


class BaseModelClient(ABC):
    """
    Abstract base class cho model clients
    """

    def __init__(self, model_name: str, api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or self._get_api_key()

    @abstractmethod
    def _get_api_key(self) -> str:
        """Get API key from environment"""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> ModelResponse:
        """
        Generate response from model

        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Model-specific parameters

        Returns:
            ModelResponse
        """
        pass

    @abstractmethod
    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict],
        **kwargs
    ) -> ModelResponse:
        """
        Generate với function calling

        Args:
            prompt: Input prompt
            tools: List of tool definitions
            **kwargs: Additional parameters

        Returns:
            ModelResponse
        """
        pass


class GeminiFlashClient(BaseModelClient):
    """
    Google Gemini Flash 1.5
    - Ultra fast, ultra cheap
    - Best for: Simple queries, CRUD, classification
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("gemini-1.5-flash", api_key)

    def _get_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> ModelResponse:
        """
        Generate với Gemini Flash

        Uses google.generativeai library
        """
        import google.generativeai as genai
        import time

        genai.configure(api_key=self.api_key)

        model = genai.GenerativeModel(self.model_name)

        start_time = time.time()

        # Generate
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )
        )

        latency = (time.time() - start_time) * 1000

        # Extract content
        content = response.text

        # Token counting (approximate)
        input_tokens = len(prompt.split()) * 1.3  # Rough estimate
        output_tokens = len(content.split()) * 1.3

        # Cost calculation (per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * 0.000075
        output_cost = (output_tokens / 1_000_000) * 0.0003
        total_cost = input_cost + output_cost

        return ModelResponse(
            content=content,
            model=self.model_name,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            cost=total_cost,
            latency_ms=latency
        )

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict],
        **kwargs
    ) -> ModelResponse:
        """Gemini Flash function calling"""
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)

        model = genai.GenerativeModel(
            self.model_name,
            tools=tools
        )

        response = await model.generate_content_async(prompt)

        return ModelResponse(
            content=response.text,
            model=self.model_name,
            metadata={"function_calls": response.candidates[0].function_calls if hasattr(response.candidates[0], 'function_calls') else None}
        )


class GeminiProClient(BaseModelClient):
    """
    Google Gemini Pro 1.5
    - Fast, cheap, good quality
    - Best for: Screening, medium complexity tasks
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("gemini-1.5-pro", api_key)

    def _get_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> ModelResponse:
        """Generate với Gemini Pro"""
        import google.generativeai as genai
        import time

        genai.configure(api_key=self.api_key)

        model = genai.GenerativeModel(self.model_name)

        start_time = time.time()

        response = await model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )
        )

        latency = (time.time() - start_time) * 1000

        content = response.text

        # Token counting
        input_tokens = len(prompt.split()) * 1.3
        output_tokens = len(content.split()) * 1.3

        # Cost
        input_cost = (input_tokens / 1_000_000) * 0.00035
        output_cost = (output_tokens / 1_000_000) * 0.00105
        total_cost = input_cost + output_cost

        return ModelResponse(
            content=content,
            model=self.model_name,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            cost=total_cost,
            latency_ms=latency
        )

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict],
        **kwargs
    ) -> ModelResponse:
        """Gemini Pro function calling"""
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)

        model = genai.GenerativeModel(
            self.model_name,
            tools=tools
        )

        response = await model.generate_content_async(prompt)

        return ModelResponse(
            content=response.text,
            model=self.model_name
        )


class ClaudeSonnetClient(BaseModelClient):
    """
    Anthropic Claude 3.5 Sonnet
    - Best reasoning, context window 200k
    - Best for: Analysis, complex reasoning, discovery
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("claude-3-5-sonnet-20241022", api_key)

    def _get_api_key(self) -> str:
        return os.getenv("ANTHROPIC_API_KEY", "")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> ModelResponse:
        """Generate với Claude Sonnet"""
        from anthropic import AsyncAnthropic
        import time

        client = AsyncAnthropic(api_key=self.api_key)

        start_time = time.time()

        message = await client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt}
            ],
            **kwargs
        )

        latency = (time.time() - start_time) * 1000

        content = message.content[0].text

        # Token counting from response
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        # Cost
        input_cost = (input_tokens / 1_000_000) * 0.003
        output_cost = (output_tokens / 1_000_000) * 0.015
        total_cost = input_cost + output_cost

        return ModelResponse(
            content=content,
            model=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=total_cost,
            latency_ms=latency
        )

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict],
        **kwargs
    ) -> ModelResponse:
        """Claude tool use"""
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.api_key)

        message = await client.messages.create(
            model=self.model_name,
            max_tokens=2000,
            tools=tools,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return ModelResponse(
            content=message.content[0].text if message.content else "",
            model=self.model_name,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            metadata={"tool_use": message.stop_reason == "tool_use"}
        )


class GPT4oClient(BaseModelClient):
    """
    OpenAI GPT-4o
    - Creative, general intelligence
    - Best for: Advisory, investment planning, creative tasks
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("gpt-4o", api_key)

    def _get_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> ModelResponse:
        """Generate với GPT-4o"""
        from openai import AsyncOpenAI
        import time

        client = AsyncOpenAI(api_key=self.api_key)

        start_time = time.time()

        response = await client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        latency = (time.time() - start_time) * 1000

        content = response.choices[0].message.content

        # Token counting
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        # Cost
        input_cost = (input_tokens / 1_000_000) * 0.0025
        output_cost = (output_tokens / 1_000_000) * 0.01
        total_cost = input_cost + output_cost

        return ModelResponse(
            content=content,
            model=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=total_cost,
            latency_ms=latency
        )

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict],
        **kwargs
    ) -> ModelResponse:
        """GPT-4o function calling"""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)

        response = await client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
            tools=tools,
            **kwargs
        )

        message = response.choices[0].message

        return ModelResponse(
            content=message.content or "",
            model=self.model_name,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            metadata={
                "tool_calls": message.tool_calls if hasattr(message, 'tool_calls') else None
            }
        )


class ModelClientFactory:
    """
    Factory để tạo model clients
    """

    _clients = {}

    @classmethod
    def get_client(cls, model_name: str) -> BaseModelClient:
        """
        Get or create model client

        Args:
            model_name: Model name (gemini-flash, gemini-pro, claude-sonnet, gpt-4o)

        Returns:
            BaseModelClient instance
        """
        # Singleton pattern
        if model_name in cls._clients:
            return cls._clients[model_name]

        # Create new client
        if model_name == "gemini-flash":
            client = GeminiFlashClient()
        elif model_name == "gemini-pro":
            client = GeminiProClient()
        elif model_name == "claude-sonnet":
            client = ClaudeSonnetClient()
        elif model_name == "gpt-4o":
            client = GPT4oClient()
        else:
            raise ValueError(f"Unknown model: {model_name}")

        cls._clients[model_name] = client
        return client

    @classmethod
    def clear_cache(cls):
        """Clear client cache"""
        cls._clients.clear()


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_models():
        print("=" * 60)
        print("Multi-Model Clients Test")
        print("=" * 60)

        test_prompt = "What is the capital of Vietnam? Answer in one sentence."

        models = ["gemini-flash", "gemini-pro", "claude-sonnet", "gpt-4o"]

        for model_name in models:
            try:
                print(f"\n🤖 Testing {model_name}...")
                client = ModelClientFactory.get_client(model_name)

                response = await client.generate(
                    test_prompt,
                    temperature=0.3,
                    max_tokens=50
                )

                print(f"   ✅ Response: {response.content[:100]}")
                print(f"   💰 Cost: ${response.cost:.6f}")
                print(f"   ⏱️ Latency: {response.latency_ms:.0f}ms")
                print(f"   📊 Tokens: {response.input_tokens} in, {response.output_tokens} out")

            except Exception as e:
                print(f"   ❌ Error: {e}")

    asyncio.run(test_models())