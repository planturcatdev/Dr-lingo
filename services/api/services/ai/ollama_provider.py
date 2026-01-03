import logging
from typing import Any

import requests
from django.conf import settings

from api.utils import get_language_name

from .base import (
    BaseCompletionService,
    BaseEmbeddingService,
    BaseTranscriptionService,
    BaseTranslationService,
)

logger = logging.getLogger(__name__)


class OllamaClient:
    """Base client for Ollama API calls."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")

    def generate(self, model: str, prompt: str, **kwargs) -> str:
        """Generate text using Ollama."""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    **kwargs,
                },
                timeout=600,
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.RequestException as e:
            logger.error(f"Ollama generate error: {e}")
            raise Exception(f"Ollama API error: {str(e)}")

    def embeddings(self, model: str, prompt: str) -> list[float]:
        """Generate embeddings using Ollama."""
        try:
            logger.info(f"Generating embedding with model {model} for text: {prompt[:50]}...")
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": model, "prompt": prompt},
                timeout=600,  # Increased timeout for first load
            )
            response.raise_for_status()
            embedding = response.json().get("embedding", [])
            logger.info(f"Embedding generated successfully, dimensions: {len(embedding)}")
            return embedding
        except requests.Timeout:
            logger.error("Ollama embeddings timeout - model may be loading")
            raise Exception("Ollama timeout - model may still be loading. Try again.")
        except requests.RequestException as e:
            logger.error(f"Ollama embeddings error: {e}")
            raise Exception(f"Ollama API error: {str(e)}")

    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False


class OllamaTranslationService(BaseTranslationService):
    """Ollama-based translation service using Granite or similar models."""

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
    ):
        self.client = OllamaClient(base_url)
        self.model = model_name or getattr(settings, "OLLAMA_TRANSLATION_MODEL", "granite:latest")

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: str = "medical",
    ) -> str:
        # Convert language codes to full names for better LLM understanding
        source_name = get_language_name(source_lang)
        target_name = get_language_name(target_lang)

        prompt = f"""System:
You are a professional medical translator. Translate accurately while being culturally sensitive.
Map medical terms to understandable language for patients.
Return ONLY the translated text, no explanations.

User:
Translate from {source_name} to {target_name}:
{text}

Assistant:
"""

        result = self.client.generate(self.model, prompt)
        return result.strip()

    def translate_with_context(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        conversation_history: list[dict] | None = None,
        sender_type: str = "patient",
        rag_context: str | None = None,
    ) -> str:
        # Convert language codes to full names for better LLM understanding
        source_name = get_language_name(source_lang)
        target_name = get_language_name(target_lang)

        context_str = ""
        if conversation_history:
            context_str = "Previous conversation:\n"
            for msg in conversation_history[-5:]:
                context_str += f"- {msg.get('sender_type', 'unknown')}: {msg.get('text', '')}\n"

        rag_str = ""
        if rag_context:
            rag_str = f"### Reference Information\n{rag_context}\n"

        prompt = f"""System:
You are an expert medical translator specializing in {target_name}.
Your goal is to provide accurate, culturally respectful translations for a {sender_type}.

CRITICAL INSTRUCTIONS:
1. Use the "Reference Information" below as your primary source of truth for terminology, grammar rules, and linguistic style.
2. The Reference Information contains natural spoken language examples and transcriptions. Use them to infer correct {target_name} phrasing, noun class usage, and cultural tone.
3. If the Reference Information contains specific noun class rules, APPLY THEM STRICTLY.
4. Do not transliterate. Prioritize natural, idiomatic {target_name} as shown in the examples.
5. Return ONLY the translated text.

User:
{rag_str}

### Conversation History
{context_str}

### Task
Translate the following text from {source_name} to {target_name}:
"{text}"

Assistant:
"""
        logger.debug(f"Translation Prompt:\n{prompt}")

        result = self.client.generate(self.model, prompt)
        return result.strip()


class OllamaEmbeddingService(BaseEmbeddingService):
    """Ollama-based embedding service using nomic-embed-text or similar."""

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        dimensions: int = 768,
    ):
        self.client = OllamaClient(base_url)
        self.model = model_name or getattr(settings, "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest")
        self._dimensions = dimensions

    def generate_embedding(self, text: str) -> list[float]:
        return self.client.embeddings(self.model, text)

    def get_dimensions(self) -> int:
        return self._dimensions


class OllamaTranscriptionService(BaseTranscriptionService):
    """
    Ollama-based transcription service.

    Note: Ollama doesn't natively support audio transcription.
    This implementation uses a workaround with Whisper via external service
    or falls back to Gemini for audio.
    """

    def __init__(self, base_url: str | None = None):
        self.client = OllamaClient(base_url)
        self._whisper_url = getattr(settings, "WHISPER_API_URL", "http://localhost:9000")

    def transcribe(
        self,
        audio_data: bytes,
        source_lang: str = "auto",
    ) -> dict[str, Any]:
        """
        Transcribe audio using external Whisper service.

        If Whisper service is not available, returns an error.
        Consider using GeminiTranscriptionService as fallback.
        """
        if len(audio_data) < 500:
            return {
                "transcription": "",
                "detected_language": source_lang if source_lang != "auto" else "unknown",
                "success": False,
                "error": "Audio file is too small or empty",
            }

        try:
            # Try external Whisper API
            response = requests.post(
                f"{self._whisper_url}/transcribe",
                files={"audio": ("audio.webm", audio_data, "audio/webm")},
                data={"language": source_lang if source_lang != "auto" else ""},
                timeout=600,
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "transcription": result.get("text", ""),
                    "detected_language": result.get("language", source_lang),
                    "success": True,
                }
            else:
                return {
                    "transcription": "",
                    "detected_language": "unknown",
                    "success": False,
                    "error": f"Whisper API error: {response.status_code}",
                }

        except requests.RequestException as e:
            logger.warning(f"Whisper service unavailable: {e}")
            return {
                "transcription": "",
                "detected_language": "unknown",
                "success": False,
                "error": "Whisper service unavailable. Use Gemini for transcription.",
            }


class OllamaCompletionService(BaseCompletionService):
    """Ollama-based text completion service."""

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
    ):
        self.client = OllamaClient(base_url)
        self.model = model_name or getattr(settings, "OLLAMA_COMPLETION_MODEL", "granite3.3:8b")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        return self.client.generate(
            self.model,
            prompt,
            options={"num_predict": max_tokens, "temperature": temperature},
        )

    def generate_with_context(
        self,
        prompt: str,
        context: str,
        max_tokens: int = 1000,
    ) -> str:
        full_prompt = f"""System:
Use the following context to answer the question.

User:
Context:
{context}

Question:
{prompt}

Assistant:
"""
        return self.generate(full_prompt, max_tokens)
