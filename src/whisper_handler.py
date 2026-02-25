"""Local audio transcription using faster-whisper."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WhisperHandler:
    """Handler for local audio transcription using faster-whisper."""

    def __init__(self, model_size: str = "base") -> None:
        """
        Initialize the Whisper handler.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
                       Use "base" for Pi 5 balance of speed/accuracy
        """
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError(
                "faster-whisper is required for local transcription. "
                "Install with: pip install faster-whisper"
            )

        logger.info(f"Loading Whisper model: {model_size}")

        # Use CPU with INT8 quantization for Pi efficiency
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8"
        )

        self.model_size = model_size
        logger.info(f"Whisper model loaded: {model_size} (CPU, INT8)")

    def transcribe(self, audio_path: str, language: str = "zh") -> str:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file (supports most formats via ffmpeg)
            language: Language code (default "zh" for Chinese/Cantonese)

        Returns:
            Transcribed text
        """
        logger.info(f"Transcribing audio: {audio_path}")

        try:
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=True  # Voice activity detection for cleaner results
            )

            # Combine all segments
            transcribed_text = " ".join(segment.text.strip() for segment in segments)

            logger.info(f"Transcription complete: {transcribed_text[:100]}...")
            logger.debug(f"Detected language: {info.language} (prob: {info.language_probability:.2f})")

            return transcribed_text

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
