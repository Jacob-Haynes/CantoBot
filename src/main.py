"""Main entry point for the Cantonese AI Tutor Bot."""

import logging
import signal
import sys
from pathlib import Path
from functools import wraps
import asyncio
import os
from typing import Callable, Any, Awaitable

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from .config import Config
from .database import DatabaseManager
from .gemini_handler import GeminiHandler
from .tts_handler import TTSHandler
from .health_check import HealthCheckServer
from .prompts import (
    WELCOME_MESSAGE,
    ERROR_GENERIC,
    ERROR_PROCESSING_AUDIO,
    ERROR_PROCESSING_TEXT,
    ERROR_TTS_GENERATION,
    TEMP_DIR
)

# Logger will be configured after loading config
logger = logging.getLogger(__name__)


class CantoneseBot:
    """Main bot application class."""

    def __init__(self) -> None:
        # Load configuration first
        try:
            self.config: Config = Config()
        except ValueError as e:
            print(f"Configuration error: {e}", file=sys.stderr)
            sys.exit(1)

        # Configure logging with loaded config
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=self.config.log_level,
            force=True
        )

        logger.info("Initializing Cantonese AI Tutor Bot...")

        # Initialize components
        self.db: DatabaseManager = DatabaseManager(self.config.db_path)
        self.gemini: GeminiHandler = GeminiHandler(
            self.config.google_api_key,
            self.config.gemini_model
        )
        self.tts: TTSHandler = TTSHandler()

        # Store allowed user ID for decorator
        self.allowed_user_id: int = self.config.allowed_user_id

        # Initialize health check server
        self.health_server: HealthCheckServer = HealthCheckServer(
            port=self.config.health_check_port,
            health_check_func=self.health_check
        )

        logger.info("Bot components initialized")

    def authorized_only(
        self,
        func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]
    ) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]:
        """Decorator to restrict handlers to authorized user only."""
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
            user_id: int = update.effective_user.id
            if user_id != self.allowed_user_id:
                logger.warning(f"Unauthorized access attempt from user_id: {user_id}")
                return
            return await func(update, context)
        return wrapper

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        logger.info("Received /start command")

        # Get user facts
        user_facts: dict[str, str] = await self.db.get_user_facts()

        # Build facts display
        facts_display: str = "\n".join([f"• {key}: {value}" for key, value in user_facts.items()])

        full_message: str = f"{WELCOME_MESSAGE}\n\nYour profile:\n{facts_display}"

        await update.message.reply_text(full_message)

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle voice messages."""
        logger.info("Received voice message")

        voice_file: Any = None
        audio_file_path: str | None = None
        tts_file_path: str | None = None

        try:
            # Download voice file
            voice_file = await update.message.voice.get_file()
            audio_file_path = f"{TEMP_DIR}/voice_{update.message.message_id}.ogg"
            await voice_file.download_to_drive(audio_file_path)
            logger.info(f"Downloaded voice file: {audio_file_path}")

            # Get conversation history and user facts
            conversation_history: list[dict[str, str]] = await self.db.get_recent_history()
            user_facts: dict[str, str] = await self.db.get_user_facts()

            # Process audio with Gemini
            response_text: str = await self.gemini.process_audio(
                audio_file_path,
                conversation_history,
                user_facts
            )

            # Save messages to database
            await self.db.save_message("user", "[voice message]", "audio")
            await self.db.save_message("model", response_text, "text")

            # Send text response
            await update.message.reply_text(response_text)

            # Generate and send TTS audio
            try:
                tts_file_path = f"{TEMP_DIR}/tts_{update.message.message_id}.mp3"
                await self.tts.generate_speech(response_text, tts_file_path)

                with open(tts_file_path, 'rb') as audio:
                    await update.message.reply_voice(audio)

            except Exception as e:
                logger.error(f"TTS generation failed: {e}")
                await update.message.reply_text(ERROR_TTS_GENERATION)

        except Exception as e:
            logger.error(f"Error handling voice message: {e}", exc_info=True)
            await update.message.reply_text(ERROR_PROCESSING_AUDIO)

        finally:
            # Cleanup temp files
            for file_path in [audio_file_path, tts_file_path]:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.debug(f"Cleaned up: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup {file_path}: {e}")

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages."""
        logger.info(f"Received text message: {update.message.text[:50]}...")

        tts_file_path: str | None = None

        try:
            # Get conversation history and user facts
            conversation_history: list[dict[str, str]] = await self.db.get_recent_history()
            user_facts: dict[str, str] = await self.db.get_user_facts()

            # Process text with Gemini
            response_text: str = await self.gemini.process_text(
                update.message.text,
                conversation_history,
                user_facts
            )

            # Save messages to database
            await self.db.save_message("user", update.message.text, "text")
            await self.db.save_message("model", response_text, "text")

            # Send text response
            await update.message.reply_text(response_text)

            # Generate and send TTS audio
            try:
                tts_file_path = f"{TEMP_DIR}/tts_{update.message.message_id}.mp3"
                await self.tts.generate_speech(response_text, tts_file_path)

                with open(tts_file_path, 'rb') as audio:
                    await update.message.reply_voice(audio)

            except Exception as e:
                logger.error(f"TTS generation failed: {e}")
                await update.message.reply_text(ERROR_TTS_GENERATION)

        except Exception as e:
            logger.error(f"Error handling text message: {e}", exc_info=True)
            await update.message.reply_text(ERROR_PROCESSING_TEXT)

        finally:
            # Cleanup temp files
            if tts_file_path and os.path.exists(tts_file_path):
                try:
                    os.remove(tts_file_path)
                    logger.debug(f"Cleaned up: {tts_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup {tts_file_path}: {e}")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors in the bot."""
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)

        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(ERROR_GENERIC)
            except Exception as e:
                logger.error(f"Failed to send error message: {e}")

    async def health_check(self) -> dict[str, bool | str]:
        """
        Perform health check on bot components.

        Returns:
            Dictionary with health status information
        """
        health_data: dict[str, bool | str] = {
            "status": "ok",
            "healthy": True
        }

        # Check database connectivity
        try:
            await self.db.get_user_facts()
            health_data["database"] = "ok"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_data["database"] = f"error: {str(e)}"
            health_data["healthy"] = False
            health_data["status"] = "degraded"

        return health_data

    async def start(self) -> None:
        """Start the bot."""
        # Initialize database
        await self.db.initialize_db()

        # Start health check server
        self.health_server.start()

        # Build application
        app = Application.builder().token(self.config.telegram_bot_token).build()

        # Register handlers with authorization
        app.add_handler(CommandHandler("start", self.authorized_only(self.start_command)))
        app.add_handler(MessageHandler(filters.VOICE, self.authorized_only(self.handle_voice)))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.authorized_only(self.handle_text)))

        # Register error handler
        app.add_error_handler(self.error_handler)

        # Setup graceful shutdown
        def signal_handler(sig, frame):
            logger.info("Received shutdown signal, stopping bot...")
            asyncio.create_task(app.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start polling
        logger.info("Starting bot polling...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()

        logger.info("Bot is running! Press Ctrl+C to stop.")

        # Keep running until stopped
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            logger.info("Bot stopped")
        finally:
            # Stop health check server
            self.health_server.stop()

            await app.updater.stop()
            await app.stop()
            await app.shutdown()

            # Cleanup temp directory
            try:
                temp_path = Path(TEMP_DIR)
                for file in temp_path.glob("*"):
                    file.unlink()
                logger.info("Cleaned up temp directory")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {e}")


def main() -> None:
    """Main entry point."""
    bot: CantoneseBot = CantoneseBot()
    asyncio.run(bot.start())


if __name__ == "__main__":
    main()
