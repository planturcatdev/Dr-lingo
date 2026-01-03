import logging
import os
import tempfile

from django.conf import settings

logger = logging.getLogger(__name__)

# Auto-accept Coqui TTS license (CPML for non-commercial use)
os.environ["COQUI_TOS_AGREED"] = "1"

# TTS model instance (lazy loaded)
_tts_model = None

# Language code mapping for XTTS
XTTS_LANGUAGE_MAP = {
    "en": "en",
    "eng": "en",
    "es": "es",
    "spa": "es",
    "fr": "fr",
    "fra": "fr",
    "de": "de",
    "deu": "de",
    "it": "it",
    "ita": "it",
    "pt": "pt",
    "por": "pt",
    "pl": "pl",
    "pol": "pl",
    "tr": "tr",
    "tur": "tr",
    "ru": "ru",
    "rus": "ru",
    "nl": "nl",
    "nld": "nl",
    "cs": "cs",
    "ces": "cs",
    "ar": "ar",
    "ara": "ar",
    "zh": "zh-cn",
    "zho": "zh-cn",
    "ja": "ja",
    "jpn": "ja",
    "hu": "hu",
    "hun": "hu",
    "ko": "ko",
    "kor": "ko",
    # South African languages - fallback to English for now
    # XTTS doesn't natively support these, but we can try
    "zul": "en",  # isiZulu
    "xho": "en",  # isiXhosa
    "afr": "en",  # Afrikaans (close to Dutch/English)
    "sot": "en",  # Sesotho
    "tsn": "en",  # Setswana
    "nso": "en",  # Sepedi
    "ssw": "en",  # siSwati
    "ven": "en",  # Tshivenda
    "tso": "en",  # Xitsonga
    "nbl": "en",  # isiNdebele
}

# Default speaker reference audio paths
SPEAKER_WAV_DIR = os.path.join(settings.BASE_DIR, "media", "tts_speakers")
DOCTOR_SPEAKER_WAV = os.path.join(SPEAKER_WAV_DIR, "doctor_reference.wav")
PATIENT_SPEAKER_WAV = os.path.join(SPEAKER_WAV_DIR, "patient_reference.wav")
DEFAULT_SPEAKER_WAV = os.path.join(SPEAKER_WAV_DIR, "default_speaker.wav")


def get_speaker_wav(speaker_type: str = None) -> str:
    """Get the appropriate speaker reference file based on speaker type."""
    if speaker_type == "doctor" and os.path.exists(DOCTOR_SPEAKER_WAV):
        return DOCTOR_SPEAKER_WAV
    elif speaker_type == "patient" and os.path.exists(PATIENT_SPEAKER_WAV):
        return PATIENT_SPEAKER_WAV
    elif os.path.exists(DEFAULT_SPEAKER_WAV):
        return DEFAULT_SPEAKER_WAV
    # Fallback to any available speaker file
    for wav in [DOCTOR_SPEAKER_WAV, PATIENT_SPEAKER_WAV]:
        if os.path.exists(wav):
            return wav
    return None


def get_tts_model():
    """Get or initialize the TTS model (lazy loading)."""
    global _tts_model

    if _tts_model is None:
        try:
            # Fix for PyTorch 2.6+ weights_only default change
            # TTS models need to load with weights_only=False
            import torch

            original_load = torch.load

            def patched_load(*args, **kwargs):
                # Force weights_only=False for TTS model loading
                if "weights_only" not in kwargs:
                    kwargs["weights_only"] = False
                return original_load(*args, **kwargs)

            torch.load = patched_load

            from TTS.api import TTS

            logger.info("Loading XTTS v2 model...")
            _tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            logger.info("XTTS v2 model loaded successfully")

            # Restore original torch.load
            torch.load = original_load

        except ImportError:
            logger.error("TTS library not installed. Run: pip install TTS")
            raise
        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}")
            raise

    return _tts_model


def get_xtts_language(lang_code: str) -> str:
    """Convert language code to XTTS-compatible format."""
    return XTTS_LANGUAGE_MAP.get(lang_code.lower(), "en")


def text_to_speech(
    text: str,
    language: str,
    speaker_wav: str = None,
    speaker_type: str = None,
    output_path: str = None,
) -> dict:
    """
    Convert text to speech using XTTS v2.

    Args:
        text: Text to synthesize
        language: Target language code
        speaker_wav: Path to reference speaker audio (for voice cloning)
        speaker_type: "doctor" or "patient" - selects appropriate voice
        output_path: Path to save output audio (optional, uses temp file if not provided)

    Returns:
        dict with success status and file_path or error
    """
    try:
        tts = get_tts_model()

        # Get XTTS-compatible language code
        xtts_lang = get_xtts_language(language)

        # Use speaker_type to select voice if no explicit speaker_wav
        if speaker_wav is None:
            speaker_wav = get_speaker_wav(speaker_type)

        # Check if speaker file exists
        if speaker_wav is None or not os.path.exists(speaker_wav):
            logger.error(f"Speaker file not found: {speaker_wav}")
            return {
                "success": False,
                "error": f"Speaker reference file not found. Add WAV files to {SPEAKER_WAV_DIR}",
            }

        # Generate output path if not provided
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".wav")

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        logger.info(f"Generating TTS: lang={xtts_lang}, text_len={len(text)}")

        # Generate speech with speaker reference
        tts.tts_to_file(
            text=text,
            speaker_wav=speaker_wav,
            language=xtts_lang,
            file_path=output_path,
        )

        logger.info(f"TTS generated successfully: {output_path}")

        return {
            "success": True,
            "file_path": output_path,
            "language": xtts_lang,
        }

    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def is_tts_available() -> bool:
    """Check if TTS service is available."""
    try:
        import importlib.util

        return importlib.util.find_spec("TTS") is not None
    except ImportError:
        return False
