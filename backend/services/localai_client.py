"""
LocalAI Integration Client for SomniProperty

Integrates with self-hosted LocalAI (OpenAI-compatible AI inference) for:
- Chat completions (conversational AI)
- Text embeddings (semantic search)
- Image analysis (photo understanding)
- Audio transcription (voice messages)
- Multi-modal AI capabilities
- Drop-in replacement for OpenAI/Ollama

LocalAI Service: localai.ai.svc.cluster.local:8080
Documentation: https://localai.io/docs
API Docs: https://localai.io/api-reference
OpenAI Compatibility: https://localai.io/features/openai-compatibility
"""

import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
import httpx
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """Chat message roles"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class ImageDetail(Enum):
    """Image analysis detail level"""
    AUTO = "auto"
    LOW = "low"
    HIGH = "high"


class ChatMessage(BaseModel):
    """Chat message model"""
    role: str
    content: Union[str, List[Dict[str, Any]]]  # String or multi-modal content
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None


class ChatCompletionResponse(BaseModel):
    """Chat completion response model"""
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


class EmbeddingResponse(BaseModel):
    """Embedding response model"""
    object: str
    data: List[Dict[str, Any]]
    model: str
    usage: Dict[str, int]


class ImageAnalysisResponse(BaseModel):
    """Image analysis response model"""
    description: str
    objects: Optional[List[str]] = []
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class TranscriptionResponse(BaseModel):
    """Audio transcription response model"""
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None
    segments: Optional[List[Dict[str, Any]]] = []


class LocalAIClient:
    """Client for interacting with LocalAI API (OpenAI-compatible)"""

    def __init__(
        self,
        base_url: str = "http://localai.ai.svc.cluster.local:8080",
        api_key: Optional[str] = None,
        default_model: str = "galatolo-Q4_K.gguf",  # Faster quantized model
        timeout: int = 120  # Higher timeout for AI inference
    ):
        """
        Initialize LocalAI client

        Args:
            base_url: LocalAI service URL
            api_key: API key (optional, for authentication)
            default_model: Default model to use
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    def _headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    # ========================================
    # Model Management
    # ========================================

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models

        Returns:
            List of available models
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/v1/models",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []

        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    async def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get model information

        Args:
            model_id: Model ID

        Returns:
            Model information or None on failure
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/v1/models/{model_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                return response.json()
            return None

        except Exception as e:
            logger.error(f"Error getting model: {e}")
            return None

    # ========================================
    # Chat Completions
    # ========================================

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[List[str]] = None,
        stream: bool = False,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[Union[str, Dict[str, str]]] = None
    ) -> Optional[ChatCompletionResponse]:
        """
        Create a chat completion

        Use for:
        - Conversational AI (chatbots)
        - Text generation
        - Question answering
        - Task automation
        - Code generation

        Args:
            messages: List of chat messages
            model: Model to use (default: self.default_model)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Frequency penalty (-2 to 2)
            presence_penalty: Presence penalty (-2 to 2)
            stop: Stop sequences
            stream: Stream response (not implemented in this version)
            functions: Function definitions for function calling
            function_call: Control function calling behavior

        Returns:
            Chat completion response or None on failure
        """
        try:
            payload = {
                "model": model or self.default_model,
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content
                    }
                    for msg in messages
                ],
                "temperature": temperature,
                "top_p": top_p,
                "frequency_penalty": frequency_penalty,
                "presence_penalty": presence_penalty,
                "stream": stream
            }

            if max_tokens:
                payload["max_tokens"] = max_tokens
            if stop:
                payload["stop"] = stop
            if functions:
                payload["functions"] = functions
            if function_call:
                payload["function_call"] = function_call

            response = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers(),
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                return ChatCompletionResponse(
                    id=data.get("id"),
                    object=data.get("object"),
                    created=data.get("created"),
                    model=data.get("model"),
                    choices=data.get("choices", []),
                    usage=data.get("usage", {})
                )
            else:
                logger.error(f"Failed to create chat completion: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating chat completion: {e}")
            return None

    async def simple_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Optional[str]:
        """
        Simple completion helper (single prompt → response)

        Args:
            prompt: Input prompt
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            Generated text or None on failure
        """
        messages = [ChatMessage(role=MessageRole.USER.value, content=prompt)]
        response = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        if response and response.choices:
            return response.choices[0].get("message", {}).get("content")
        return None

    # ========================================
    # Embeddings
    # ========================================

    async def create_embedding(
        self,
        input_text: Union[str, List[str]],
        model: Optional[str] = None
    ) -> Optional[EmbeddingResponse]:
        """
        Create embeddings for text

        Use for:
        - Semantic search
        - Similarity comparison
        - Clustering
        - Classification

        Args:
            input_text: Text or list of texts to embed
            model: Embedding model to use

        Returns:
            Embedding response or None on failure
        """
        try:
            payload = {
                "model": model or "text-embedding-ada-002",
                "input": input_text
            }

            response = await self.client.post(
                f"{self.base_url}/v1/embeddings",
                headers=self._headers(),
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                return EmbeddingResponse(
                    object=data.get("object"),
                    data=data.get("data", []),
                    model=data.get("model"),
                    usage=data.get("usage", {})
                )
            else:
                logger.error(f"Failed to create embedding: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            return None

    async def get_embedding_vector(self, text: str, model: Optional[str] = None) -> Optional[List[float]]:
        """
        Get embedding vector for text (helper)

        Args:
            text: Text to embed
            model: Embedding model

        Returns:
            Embedding vector or None on failure
        """
        response = await self.create_embedding(text, model)
        if response and response.data:
            return response.data[0].get("embedding")
        return None

    # ========================================
    # Image Analysis
    # ========================================

    async def analyze_image(
        self,
        image_url: Optional[str] = None,
        image_data: Optional[bytes] = None,
        prompt: str = "Describe this image in detail",
        model: Optional[str] = None,
        detail: ImageDetail = ImageDetail.AUTO
    ) -> Optional[str]:
        """
        Analyze an image using vision model

        Use for:
        - Work order photo analysis
        - Property inspection automation
        - Damage assessment
        - Safety compliance checking

        Args:
            image_url: URL to image
            image_data: Image bytes (base64 will be handled)
            prompt: Analysis prompt
            model: Vision model to use
            detail: Detail level (auto, low, high)

        Returns:
            Analysis result or None on failure
        """
        try:
            # Build multi-modal content
            content = [
                {"type": "text", "text": prompt}
            ]

            if image_url:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                        "detail": detail.value
                    }
                })
            elif image_data:
                import base64
                b64_image = base64.b64encode(image_data).decode('utf-8')
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64_image}",
                        "detail": detail.value
                    }
                })

            messages = [ChatMessage(role=MessageRole.USER.value, content=content)]

            response = await self.chat_completion(
                messages=messages,
                model=model or "gpt-4-vision-preview"
            )

            if response and response.choices:
                return response.choices[0].get("message", {}).get("content")
            return None

        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return None

    async def detect_objects_in_image(
        self,
        image_url: Optional[str] = None,
        image_data: Optional[bytes] = None,
        model: Optional[str] = None
    ) -> Optional[List[str]]:
        """
        Detect objects in an image

        Args:
            image_url: URL to image
            image_data: Image bytes
            model: Vision model to use

        Returns:
            List of detected objects or None on failure
        """
        result = await self.analyze_image(
            image_url=image_url,
            image_data=image_data,
            prompt="List all objects visible in this image. Return only a JSON array of object names.",
            model=model
        )

        if result:
            try:
                # Try to parse as JSON array
                return json.loads(result)
            except Exception:
                # Fallback: split by commas or newlines
                return [obj.strip() for obj in result.replace("\n", ",").split(",") if obj.strip()]
        return None

    # ========================================
    # Audio Transcription
    # ========================================

    async def transcribe_audio(
        self,
        audio_file: bytes,
        model: Optional[str] = None,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        response_format: str = "json",
        temperature: float = 0.0
    ) -> Optional[TranscriptionResponse]:
        """
        Transcribe audio to text

        Use for:
        - Voice message transcription
        - Call recording transcription
        - Maintenance notes (voice input)

        Args:
            audio_file: Audio file bytes
            model: Transcription model (default: whisper-1)
            language: Audio language (ISO-639-1 code)
            prompt: Optional prompt to guide transcription
            response_format: Response format (json, text, srt, vtt)
            temperature: Sampling temperature

        Returns:
            Transcription response or None on failure
        """
        try:
            # Prepare multipart form data
            files = {
                'file': ('audio.mp3', audio_file, 'audio/mpeg')
            }

            data = {
                'model': model or 'whisper-1',
                'response_format': response_format,
                'temperature': temperature
            }

            if language:
                data['language'] = language
            if prompt:
                data['prompt'] = prompt

            response = await self.client.post(
                f"{self.base_url}/v1/audio/transcriptions",
                headers={k: v for k, v in self._headers().items() if k != "Content-Type"},
                files=files,
                data=data
            )

            if response.status_code == 200:
                result = response.json() if response_format == "json" else {"text": response.text}
                return TranscriptionResponse(
                    text=result.get("text", ""),
                    language=result.get("language"),
                    duration=result.get("duration"),
                    segments=result.get("segments", [])
                )
            else:
                logger.error(f"Failed to transcribe audio: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None

    # ========================================
    # Text Completion (Legacy)
    # ========================================

    async def text_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Legacy text completion endpoint

        Args:
            prompt: Input prompt
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            top_p: Nucleus sampling
            frequency_penalty: Frequency penalty
            presence_penalty: Presence penalty
            stop: Stop sequences

        Returns:
            Generated text or None on failure
        """
        try:
            payload = {
                "model": model or self.default_model,
                "prompt": prompt,
                "temperature": temperature,
                "top_p": top_p,
                "frequency_penalty": frequency_penalty,
                "presence_penalty": presence_penalty
            }

            if max_tokens:
                payload["max_tokens"] = max_tokens
            if stop:
                payload["stop"] = stop

            response = await self.client.post(
                f"{self.base_url}/v1/completions",
                headers=self._headers(),
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("choices"):
                    return data["choices"][0].get("text", "")
            else:
                logger.error(f"Failed to create completion: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating completion: {e}")
            return None

    # ========================================
    # SomniProperty Integration Helpers
    # ========================================

    async def analyze_work_order_photo(
        self,
        image_url: Optional[str] = None,
        image_data: Optional[bytes] = None,
        work_order_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Analyze a work order photo and generate description

        Args:
            image_url: Photo URL
            image_data: Photo bytes
            work_order_type: Work order type (plumbing, electrical, etc.)

        Returns:
            Detailed analysis or None on failure
        """
        prompt = f"""Analyze this maintenance/repair photo and provide:
1. What is the primary issue or subject?
2. What is the condition/severity?
3. What actions might be needed?
4. Any safety concerns?

Context: This is a {work_order_type or 'general'} work order photo."""

        return await self.analyze_image(
            image_url=image_url,
            image_data=image_data,
            prompt=prompt,
            detail=ImageDetail.HIGH
        )

    async def generate_work_order_description(
        self,
        issue_summary: str,
        unit_number: Optional[str] = None,
        urgency: Optional[str] = None,
        tenant_notes: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a detailed work order description

        Args:
            issue_summary: Brief issue summary
            unit_number: Unit number
            urgency: Urgency level
            tenant_notes: Additional notes from tenant

        Returns:
            Generated description or None on failure
        """
        prompt = f"""Generate a detailed work order description for property management:

Issue: {issue_summary}
Unit: {unit_number or 'N/A'}
Urgency: {urgency or 'Normal'}
Tenant Notes: {tenant_notes or 'None'}

Provide:
1. Clear problem description
2. Likely cause
3. Recommended action
4. Estimated priority
5. Parts/materials that may be needed"""

        return await self.simple_completion(prompt, temperature=0.3)

    async def classify_maintenance_request(
        self,
        request_text: str
    ) -> Optional[Dict[str, Any]]:
        """
        Classify a maintenance request using AI

        Args:
            request_text: Maintenance request text

        Returns:
            Classification result with category, urgency, etc.
        """
        prompt = f"""Classify this maintenance request and return JSON:

Request: {request_text}

Return format:
{{
    "category": "plumbing|electrical|hvac|appliance|structural|other",
    "urgency": "low|normal|high|urgent",
    "requires_contractor": true|false,
    "estimated_duration_hours": number,
    "brief_summary": "concise summary"
}}"""

        result = await self.simple_completion(prompt, temperature=0.2)

        if result:
            try:
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                logger.error(f"Error parsing classification result: {e}")

        return None

    async def generate_lease_summary(
        self,
        lease_text: str,
        focus_areas: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Generate a summary of lease agreement

        Args:
            lease_text: Full lease text
            focus_areas: Specific areas to focus on

        Returns:
            Lease summary or None on failure
        """
        focus = f"\nFocus on: {', '.join(focus_areas)}" if focus_areas else ""

        prompt = f"""Summarize this lease agreement, highlighting key terms:
{focus}

Lease:
{lease_text}

Provide:
1. Key terms (rent, duration, deposit)
2. Important clauses
3. Tenant responsibilities
4. Landlord responsibilities
5. Notable restrictions"""

        return await self.simple_completion(prompt, max_tokens=1000, temperature=0.3)

    async def semantic_search_work_orders(
        self,
        query: str,
        work_order_descriptions: List[str]
    ) -> Optional[List[tuple[int, float]]]:
        """
        Semantic search over work orders using embeddings

        Args:
            query: Search query
            work_order_descriptions: List of work order descriptions

        Returns:
            List of (index, similarity_score) tuples, sorted by relevance
        """
        try:
            # Get query embedding
            query_embedding_response = await self.create_embedding(query)
            if not query_embedding_response or not query_embedding_response.data:
                return None

            query_vector = query_embedding_response.data[0].get("embedding")

            # Get embeddings for all descriptions
            descriptions_response = await self.create_embedding(work_order_descriptions)
            if not descriptions_response or not descriptions_response.data:
                return None

            # Calculate cosine similarity
            import numpy as np

            query_vec = np.array(query_vector)
            results = []

            for i, embed_data in enumerate(descriptions_response.data):
                desc_vec = np.array(embed_data.get("embedding"))
                similarity = np.dot(query_vec, desc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(desc_vec))
                results.append((i, float(similarity)))

            # Sort by similarity (descending)
            results.sort(key=lambda x: x[1], reverse=True)

            return results

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return None


# ========================================
# Singleton instance management
# ========================================

_localai_client: Optional[LocalAIClient] = None


def get_localai_client(
    base_url: str = "http://localai.ai.svc.cluster.local:8080",
    api_key: Optional[str] = None,
    default_model: str = "gpt-4o"
) -> LocalAIClient:
    """Get singleton LocalAI client instance"""
    global _localai_client
    if _localai_client is None:
        _localai_client = LocalAIClient(
            base_url=base_url,
            api_key=api_key,
            default_model=default_model
        )
    return _localai_client


async def close_localai_client():
    """Close singleton LocalAI client"""
    global _localai_client
    if _localai_client:
        await _localai_client.close()
        _localai_client = None
