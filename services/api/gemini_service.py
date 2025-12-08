"""
Gemini AI service for translation and multimodal processing.

This service handles:
- Real-time translation between languages
- Image understanding and description
- Context-aware medical translation
- Multimodal content processing
"""

import os
from typing import Any, Dict

import google.generativeai as genai
from django.conf import settings


class GeminiTranslationService:
    """
    Service for handling Gemini AI translation and multimodal features.
    """

    def __init__(self):
        """Initialize Gemini with API key from settings."""
        api_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
        if not api_key or api_key == "your-gemini-api-key-here":
            raise ValueError(
                "GEMINI_API_KEY not configured. Please add your API key to services/.env file. "
                "Get your key from: https://makersuite.google.com/app/apikey"
            )

        try:
            genai.configure(api_key=api_key)
            # Use latest Gemini models
            self.model = genai.GenerativeModel("gemini-2.0-flash")
            self.vision_model = genai.GenerativeModel("gemini-2.0-flash")
        except Exception as e:
            raise ValueError(f"Failed to initialize Gemini AI: {str(e)}")

    def translate_text(self, text: str, source_lang: str, target_lang: str, context: str = "medical") -> str:
        """
        Translate text from source language to target language.

        Args:
            text: Text to translate
            source_lang: Source language code (e.g., 'en', 'es', 'fr')
            target_lang: Target language code
            context: Context for translation (medical, general, etc.)

        Returns:
            Translated text
        """
        prompt = f"""
        You are a professional medical translator. Translate the following text from {source_lang} to {target_lang}.
        Before translating, you MUST perform a strict pre-check to confirm that the input text is actually written in {source_lang},
        Instead, return an error message stating: The provided text is not written in {source_lang}. Please provide text in the correct source language for translation.
        Only if the text is confidently identified as {source_lang} may you proceed with the translation

        Context: {context}

        Important guidelines:
        - Maintain medical accuracy and terminology
        - Be culturally sensitive
        - Keep the tone appropriate for patient-doctor communication
        - Only return the translated text, no explanations

        Text to translate:
        {text}
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            raise Exception(f"Translation failed: {str(e)}")

    def analyze_image(self, image_data: bytes, language: str = "en", context: str = "medical") -> Dict[str, Any]:
        """
        Analyze an image and provide description in specified language.

        Args:
            image_data: Image bytes
            language: Language for description
            context: Context for analysis

        Returns:
            Dictionary with description and analysis
        """
        prompt = f"""
        Analyze this medical image and provide:
        1. A clear description in {language}
        2. Any visible symptoms or conditions
        3. Important details a doctor should know

        Format your response as a clear, professional medical description.
        """

        try:
            response = self.vision_model.generate_content([prompt, image_data])
            return {"description": response.text.strip(), "language": language, "success": True}
        except Exception as e:
            return {"description": f"Image analysis failed: {str(e)}", "language": language, "success": False}

    def transcribe_audio(self, audio_data: bytes, source_lang: str = "auto") -> Dict[str, Any]:
        """
        Transcribe audio using Gemini multimodal capabilities.

        Args:
            audio_data: Audio file bytes (webm, mp3, wav, etc.)
            source_lang: Source language code or 'auto' for detection

        Returns:
            Dictionary with transcription and detected language
        """
        prompt = f"""
        Transcribe this audio recording accurately.

        {"Detect the language automatically." if source_lang == "auto" else f"The audio is in {source_lang}."}

        Provide:
        1. The exact transcription
        2. The detected language code (e.g., 'en', 'es', 'fr')

        Format your response as:
        LANGUAGE: [language_code]
        TRANSCRIPTION: [transcribed text]
        """

        try:
            # Upload audio file to Gemini
            import tempfile

            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
                temp_audio.write(audio_data)
                temp_audio_path = temp_audio.name

            # Upload file
            audio_file = genai.upload_file(temp_audio_path)

            # Generate transcription
            response = self.model.generate_content([prompt, audio_file])
            result_text = response.text.strip()

            # Parse response
            lines = result_text.split("\n")
            detected_lang = "unknown"
            transcription = ""

            for line in lines:
                if line.startswith("LANGUAGE:"):
                    detected_lang = line.replace("LANGUAGE:", "").strip()
                elif line.startswith("TRANSCRIPTION:"):
                    transcription = line.replace("TRANSCRIPTION:", "").strip()

            # If parsing failed, use entire response as transcription
            if not transcription:
                transcription = result_text

            # Clean up temp file
            import os

            os.unlink(temp_audio_path)

            return {"transcription": transcription, "detected_language": detected_lang, "success": True}

        except Exception as e:
            return {"transcription": "", "detected_language": "unknown", "success": False, "error": str(e)}

    def translate_with_context(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        conversation_history: list = None,
        sender_type: str = "patient",
        rag_context: str = None,
    ) -> str:
        """
        Translate with conversation context and RAG context for better accuracy.

        Args:
            text: Text to translate
            source_lang: Source language
            target_lang: Target language
            conversation_history: Previous messages for context
            sender_type: 'patient' or 'doctor'
            rag_context: Additional context from RAG (cultural, medical info)

        Returns:
            Translated text with context awareness
        """
        context_str = ""
        if conversation_history:
            context_str = "\n\nPrevious conversation:\n"
            for msg in conversation_history[-5:]:  # Last 5 messages
                context_str += f"- {msg.get('sender_type', 'unknown')}: {msg.get('text', '')}\n"

        rag_context_str = ""
        if rag_context:
            rag_context_str = f"\n\nRELEVANT CONTEXT (Cultural & Medical):\n{rag_context}\n"

        prompt = f"""
        You are translating a {sender_type}'s message in a medical consultation.

        Translate from {source_lang} to {target_lang}.
        {context_str}
        {rag_context_str}

        Current message to translate:
        {text}

        CRITICAL TRANSLATION GUIDELINES:
        1. FORMALITY & TONE:
           - ALWAYS translate to formal, professional medical language regardless of input tone
           - Even if the doctor writes casually (e.g., "yo wassup"), translate to proper formal medical language
           - Maintain respectful, professional tone appropriate for medical consultations

        2. CULTURAL RESTRICTIONS:
           - Strictly follow cultural guidelines and restrictions from the RAG context above
           - Adapt language to respect cultural sensitivities mentioned in patient profile
           - Use culturally appropriate terms and avoid restricted words/phrases

        3. MEDICAL ACCURACY:
           - Maintain precise medical terminology
           - Ensure clarity for patient safety

        4. OUTPUT:
           - Return ONLY the translated text
           - No explanations, notes, or metadata
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            raise Exception(f"Context-aware translation failed: {str(e)}")


# Singleton instance
_gemini_service = None


def get_gemini_service() -> GeminiTranslationService:
    """Get or create Gemini service instance."""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiTranslationService()
    return _gemini_service
