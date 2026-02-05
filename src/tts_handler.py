"""Text-to-speech handler using Edge TTS for Cantonese voice synthesis."""

import edge_tts
import re
import logging
from pathlib import Path

from .prompts import TTS_VOICE_NAME, CANTONESE_TEXT_PATTERN, TEMP_DIR

logger = logging.getLogger(__name__)


class TTSHandler:
    """Handler for converting Cantonese text to speech using Edge TTS."""

    def __init__(self, voice: str = TTS_VOICE_NAME) -> None:
        self.voice: str = voice
        # Ensure temp directory exists
        Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)

    def extract_cantonese_text(self, text: str) -> str:
        """
        Extract only Cantonese characters from the response.
        Removes Jyutping romanization and English translations.

        Args:
            text: Full response text with format "Characters (Jyutping)\nEnglish"

        Returns:
            Cantonese text only
        """
        cantonese_lines: list[str] = []

        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Try to extract text before romanization
            match = re.match(CANTONESE_TEXT_PATTERN, line)
            if match:
                cantonese_lines.append(match.group(1).strip())
            # If line starts with Chinese characters, include it
            elif line and '\u4e00' <= line[0] <= '\u9fff':
                # Remove any parenthetical content
                cantonese_text: str = re.sub(r'\s*\([^)]+\)', '', line)
                cantonese_lines.append(cantonese_text.strip())

        result: str = ' '.join(cantonese_lines)
        logger.debug(f"Extracted Cantonese text: {result}")
        return result

    async def generate_speech(self, text: str, output_path: str) -> str:
        """
        Generate speech audio file from Cantonese text.

        Args:
            text: Full response text (will be filtered to Cantonese only)
            output_path: Path where MP3 file should be saved

        Returns:
            Path to generated audio file
        """
        # Extract only Cantonese text
        cantonese_text: str = self.extract_cantonese_text(text)

        if not cantonese_text:
            logger.warning("No Cantonese text found to synthesize")
            raise ValueError("No Cantonese text found in response")

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Generate speech
        logger.info(f"Generating speech for: {cantonese_text}")
        communicate = edge_tts.Communicate(cantonese_text, self.voice)
        await communicate.save(output_path)

        logger.info(f"Speech generated: {output_path}")
        return output_path
