"""
Multi-Provider LLM Interface
Supports OpenAI, Anthropic (Claude), and Ollama for AI assistant
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Literal
from abc import ABC, abstractmethod
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

LLMProvider = Literal["openai", "anthropic", "ollama", "localai", "auto"]


class LLMMessage(BaseModel):
    """Universal message format"""
    role: str  # "system", "user", "assistant"
    content: str


class LLMResponse(BaseModel):
    """Universal response format"""
    content: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class BaseLLMProvider(ABC):
    """Base class for LLM providers"""

    def __init__(self, api_key: Optional[str] = None, model: str = "default"):
        self.api_key = api_key
        self.model = model
        self.client = httpx.AsyncClient(timeout=180.0)

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        tools: Optional[List[Dict]] = None
    ) -> LLMResponse:
        """Generate chat completion"""
        pass

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class LocalAIProvider(BaseLLMProvider):
    """LocalAI Provider (cluster-deployed, GPU-accelerated)"""

    def __init__(
        self,
        api_url: str = "http://localai.ai.svc.cluster.local:8080",
        model: str = "gpt-4o"
    ):
        super().__init__(api_key=None, model=model)
        self.api_url = api_url

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        tools: Optional[List[Dict]] = None
    ) -> LLMResponse:
        """
        LocalAI chat completion (OpenAI-compatible API)
        """
        # Convert messages to LocalAI format (same as OpenAI)
        localai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        payload = {
            "model": self.model,
            "messages": localai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Add tools if provided (LocalAI supports OpenAI-style tools)
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool.get("inputSchema", {})
                    }
                }
                for tool in tools
            ]

        try:
            response = await self.client.post(
                f"{self.api_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            choice = result["choices"][0]
            message = choice["message"]

            # Check if response is empty
            response_text = message.get("content", "")
            if not response_text and not message.get("tool_calls"):
                logger.warning(f"LocalAI returned empty response for model {self.model}")
                raise ValueError(f"LocalAI returned empty response. Model '{self.model}' may not be loaded.")

            # Extract tool calls if present
            tool_calls = None
            if "tool_calls" in message and message["tool_calls"]:
                tool_calls = [
                    {
                        "name": tc["function"]["name"],
                        "arguments": json.loads(tc["function"]["arguments"])
                    }
                    for tc in message["tool_calls"]
                ]

            return LLMResponse(
                content=response_text,
                model=self.model,
                tokens_used=result.get("usage", {}).get("total_tokens"),
                finish_reason=choice.get("finish_reason"),
                tool_calls=tool_calls
            )

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to LocalAI at {self.api_url}: {e}")
            raise ConnectionError(f"LocalAI service is not available at {self.api_url}")
        except httpx.HTTPStatusError as e:
            logger.error(f"LocalAI HTTP error: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"LocalAI API error: {e.response.text}")
        except Exception as e:
            logger.error(f"LocalAI API error: {e}")
            raise


class OllamaProvider(BaseLLMProvider):
    """Ollama LLM Provider (local, on-premise)"""

    def __init__(
        self,
        api_url: str = "http://ollama.ai.svc.cluster.local:11434",
        model: str = "llama2:latest"  # Upgraded from tinyllama (too small for complex tasks)
    ):
        super().__init__(api_key=None, model=model)
        self.api_url = api_url

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        tools: Optional[List[Dict]] = None
    ) -> LLMResponse:
        """
        Ollama chat completion
        Note: Ollama has limited tool calling support, we'll use prompt engineering
        """
        # Convert messages to Ollama format (single prompt)
        prompt = self._messages_to_prompt(messages)

        # Add tool information to system prompt if tools provided
        if tools:
            tool_descriptions = "\n".join([
                f"- {tool['name']}: {tool['description']}"
                for tool in tools
            ])
            prompt = f"Available tools:\n{tool_descriptions}\n\n{prompt}\n\nIf you need to use tools, respond with JSON containing 'tools' array."

        try:
            response = await self.client.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "top_p": 0.9
                    }
                }
            )
            response.raise_for_status()
            result = response.json()

            # Check if response is empty
            response_text = result.get("response", "")
            if not response_text:
                logger.warning(f"Ollama returned empty response for model {self.model}")
                raise ValueError(f"Ollama returned empty response. Model '{self.model}' may not be loaded.")

            return LLMResponse(
                content=response_text,
                model=self.model,
                tokens_used=result.get("eval_count"),
                finish_reason="stop"
            )

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama at {self.api_url}: {e}")
            raise ConnectionError(f"AI service (Ollama) is not available. Please ensure Ollama is running at {self.api_url}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Ollama API error: {e.response.text}")
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise

    def _messages_to_prompt(self, messages: List[LLMMessage]) -> str:
        """Convert message format to Ollama prompt"""
        prompt_parts = []
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")
        return "\n\n".join(prompt_parts) + "\n\nAssistant:"


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM Provider (GPT-4, GPT-3.5)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o"
    ):
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        super().__init__(api_key=api_key, model=model)
        self.api_url = "https://api.openai.com/v1"

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        tools: Optional[List[Dict]] = None
    ) -> LLMResponse:
        """OpenAI chat completion with native tool calling support"""

        # Convert messages to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        payload = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Add tools if provided (OpenAI native tool calling)
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool.get("inputSchema", {})
                    }
                }
                for tool in tools
            ]
            payload["tool_choice"] = "auto"

        try:
            response = await self.client.post(
                f"{self.api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            choice = result["choices"][0]
            message = choice["message"]

            # Extract tool calls if present
            tool_calls = None
            if "tool_calls" in message and message["tool_calls"]:
                tool_calls = [
                    {
                        "name": tc["function"]["name"],
                        "arguments": json.loads(tc["function"]["arguments"])
                    }
                    for tc in message["tool_calls"]
                ]

            return LLMResponse(
                content=message.get("content", ""),
                model=result["model"],
                tokens_used=result["usage"]["total_tokens"],
                finish_reason=choice["finish_reason"],
                tool_calls=tool_calls
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class AnthropicProvider(BaseLLMProvider):
    """Anthropic (Claude) LLM Provider"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022"
    ):
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        super().__init__(api_key=api_key, model=model)
        self.api_url = "https://api.anthropic.com/v1"

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        tools: Optional[List[Dict]] = None
    ) -> LLMResponse:
        """
        Anthropic chat completion with native tool calling support
        Claude has the BEST tool calling capabilities
        """

        # Separate system message from conversation
        system_message = ""
        conversation_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message += msg.content + "\n"
            else:
                conversation_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": conversation_messages
        }

        if system_message:
            payload["system"] = system_message.strip()

        # Add tools if provided (Claude native tool use)
        if tools:
            payload["tools"] = [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool.get("inputSchema", {
                        "type": "object",
                        "properties": {},
                        "required": []
                    })
                }
                for tool in tools
            ]

        try:
            response = await self.client.post(
                f"{self.api_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            # Extract content and tool calls
            content_text = ""
            tool_calls = []

            for content_block in result.get("content", []):
                if content_block["type"] == "text":
                    content_text += content_block["text"]
                elif content_block["type"] == "tool_use":
                    tool_calls.append({
                        "name": content_block["name"],
                        "arguments": content_block["input"]
                    })

            return LLMResponse(
                content=content_text,
                model=result["model"],
                tokens_used=result["usage"]["input_tokens"] + result["usage"]["output_tokens"],
                finish_reason=result["stop_reason"],
                tool_calls=tool_calls if tool_calls else None
            )

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


class LLMFactory:
    """Factory for creating LLM provider instances"""

    @staticmethod
    def create_provider(
        provider: LLMProvider,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseLLMProvider:
        """
        Create LLM provider instance

        Args:
            provider: "localai", "ollama", "openai", "anthropic", or "auto"
            api_key: API key (not needed for LocalAI/Ollama)
            model: Model name (provider-specific)
            **kwargs: Additional provider-specific arguments
        """

        if provider == "localai":
            default_model = "gpt-4o"
            api_url = kwargs.get("api_url", "http://localai.ai.svc.cluster.local:8080")
            return LocalAIProvider(
                api_url=api_url,
                model=model or default_model
            )

        elif provider == "ollama":
            default_model = "tinyllama:1.1b"
            api_url = kwargs.get("api_url", "http://ollama.ai.svc.cluster.local:11434")
            return OllamaProvider(
                api_url=api_url,
                model=model or default_model
            )

        elif provider == "openai":
            default_model = "gpt-4o"
            return OpenAIProvider(
                api_key=api_key,
                model=model or default_model
            )

        elif provider == "anthropic":
            default_model = "claude-3-5-sonnet-20241022"
            return AnthropicProvider(
                api_key=api_key,
                model=model or default_model
            )

        else:
            raise ValueError(f"Unknown provider: {provider}")

    @staticmethod
    async def create_with_fallback(
        primary_provider: Optional[LLMProvider] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> BaseLLMProvider:
        """
        Create LLM provider with automatic fallback cascade

        Fallback order:
        1. LocalAI (cluster-deployed, GPU-accelerated)
        2. Ollama (cluster-deployed, CPU)
        3. Anthropic Claude (cloud, best tool calling)
        4. OpenAI GPT-4 (cloud, widely available)

        Returns the first working provider
        """
        # Define fallback cascade
        cascade = []

        if primary_provider and primary_provider != "auto":
            # User specified a provider, try that first
            cascade.append(primary_provider)

        # Add cluster providers (free, private)
        cascade.extend(["localai", "ollama"])

        # Add cloud providers if API keys available
        if os.getenv("ANTHROPIC_API_KEY") or api_key:
            cascade.append("anthropic")
        if os.getenv("OPENAI_API_KEY") or api_key:
            cascade.append("openai")

        # Remove duplicates while preserving order
        cascade = list(dict.fromkeys(cascade))

        # Try each provider in cascade
        for provider_name in cascade:
            try:
                logger.info(f"Attempting to create LLM provider: {provider_name}")
                provider = LLMFactory.create_provider(
                    provider=provider_name,
                    api_key=api_key,
                    model=model
                )

                # Test the provider with a simple request
                test_messages = [
                    LLMMessage(role="user", content="Say 'OK' if you can hear me")
                ]
                test_response = await provider.chat_completion(
                    messages=test_messages,
                    temperature=0.1,
                    max_tokens=10
                )

                if test_response.content:
                    logger.info(f"✅ Successfully connected to {provider_name}")
                    return provider

            except ConnectionError as e:
                logger.warning(f"❌ {provider_name} connection failed: {e}")
                continue
            except ValueError as e:
                logger.warning(f"❌ {provider_name} configuration error: {e}")
                continue
            except Exception as e:
                logger.warning(f"❌ {provider_name} failed: {e}")
                continue

        # No providers worked
        raise ConnectionError(
            "All LLM providers failed. Tried: " + ", ".join(cascade) +
            ". Please ensure at least one AI service is running or configure cloud API keys."
        )


# Configuration helper
class LLMConfig(BaseModel):
    """LLM configuration"""
    provider: LLMProvider = "ollama"
    model: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load configuration from environment variables"""
        provider = os.getenv("LLM_PROVIDER", "auto")

        # Provider-specific defaults
        model_defaults = {
            "localai": "gpt-4o",
            "ollama": "tinyllama:1.1b",
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-20241022",
            "auto": None  # Will be determined by fallback
        }

        # Get API keys (used by fallback cascade if provider is "auto")
        api_key = None
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
        elif provider == "auto":
            # For auto, we'll use whichever key is available
            api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")

        return cls(
            provider=provider,
            model=os.getenv("LLM_MODEL", model_defaults.get(provider)),
            api_key=api_key,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000"))
        )


# Recommended configurations
RECOMMENDED_CONFIGS = {
    "ollama_local": LLMConfig(
        provider="ollama",
        model="tinyllama:1.1b",
        temperature=0.7,
        max_tokens=1000
    ),
    "openai_gpt4": LLMConfig(
        provider="openai",
        model="gpt-4o",
        temperature=0.7,
        max_tokens=2000
    ),
    "anthropic_claude": LLMConfig(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        temperature=0.7,
        max_tokens=2000
    ),
    "openai_gpt4_turbo": LLMConfig(
        provider="openai",
        model="gpt-4-turbo-preview",
        temperature=0.7,
        max_tokens=4000
    )
}
