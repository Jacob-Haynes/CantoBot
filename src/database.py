"""Database management for the Cantonese AI Tutor Bot using SQLite."""

import aiosqlite
from datetime import datetime
from typing import Optional
from pathlib import Path
import logging

from .prompts import DEFAULT_USER_FACTS, CONVERSATION_HISTORY_LIMIT

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Async SQLite database manager for conversation history and user facts."""

    def __init__(self, db_path: str) -> None:
        self.db_path: str = db_path
        # Ensure database directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def initialize_db(self) -> None:
        """Create database tables and seed initial user facts if needed."""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for better concurrent access
            await db.execute("PRAGMA journal_mode=WAL")

            # Create conversations table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    media_type TEXT NOT NULL
                )
            """)

            # Create user_facts table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_facts (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create vocabulary table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS vocabulary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL UNIQUE,
                    jyutping TEXT,
                    english TEXT,
                    added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    review_count INTEGER DEFAULT 0,
                    last_reviewed DATETIME
                )
            """)

            await db.commit()

            # Seed initial user facts if table is empty
            cursor = await db.execute("SELECT COUNT(*) FROM user_facts")
            count = (await cursor.fetchone())[0]

            if count == 0:
                logger.info("Seeding initial user facts")
                for key, value in DEFAULT_USER_FACTS.items():
                    await db.execute(
                        "INSERT INTO user_facts (key, value) VALUES (?, ?)",
                        (key, value)
                    )
                await db.commit()

            logger.info(f"Database initialized at {self.db_path}")

    async def save_message(self, role: str, content: str, media_type: str) -> None:
        """
        Save a conversation message to the database.

        Args:
            role: 'user' or 'model'
            content: Message content (text or file path)
            media_type: 'text' or 'audio'
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO conversations (role, content, media_type)
                VALUES (?, ?, ?)
                """,
                (role, content, media_type)
            )
            await db.commit()

        logger.debug(f"Saved message: role={role}, media_type={media_type}")

    async def get_recent_history(self, limit: int = CONVERSATION_HISTORY_LIMIT) -> list[dict[str, str]]:
        """
        Fetch recent conversation history.

        Args:
            limit: Maximum number of messages to retrieve

        Returns:
            List of dicts with 'role' and 'content' keys
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT role, content, media_type
                FROM conversations
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = await cursor.fetchall()

        # Reverse to get chronological order
        history: list[dict[str, str]] = []
        for row in reversed(rows):
            history.append({
                "role": row["role"],
                "content": row["content"],
                "media_type": row["media_type"]
            })

        logger.debug(f"Retrieved {len(history)} messages from history")
        return history

    async def get_user_facts(self) -> dict[str, str]:
        """
        Get all user facts from the database.

        Returns:
            Dictionary of user facts
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT key, value FROM user_facts")
            rows = await cursor.fetchall()

        facts: dict[str, str] = {row["key"]: row["value"] for row in rows}
        logger.debug(f"Retrieved {len(facts)} user facts")
        return facts

    async def update_user_fact(self, key: str, value: str) -> None:
        """
        Update or insert a user fact.

        Args:
            key: Fact key
            value: Fact value
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO user_facts (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, value)
            )
            await db.commit()

        logger.info(f"Updated user fact: {key}={value}")

    async def add_vocabulary_word(self, word: str, jyutping: Optional[str] = None, english: Optional[str] = None) -> bool:
        """
        Add a word to the vocabulary list.

        Args:
            word: Cantonese word (characters)
            jyutping: Optional Jyutping pronunciation
            english: Optional English translation

        Returns:
            True if word was added, False if it already existed
        """
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    """
                    INSERT INTO vocabulary (word, jyutping, english)
                    VALUES (?, ?, ?)
                    """,
                    (word, jyutping, english)
                )
                await db.commit()
                logger.info(f"Added vocabulary word: {word} ({jyutping})")
                return True
            except aiosqlite.IntegrityError:
                # Word already exists
                logger.debug(f"Word already in vocabulary: {word}")
                return False

    async def get_vocabulary_words(self, limit: Optional[int] = None) -> list[dict[str, str]]:
        """
        Get all vocabulary words from the database.

        Args:
            limit: Optional limit on number of words to return (most recent first)

        Returns:
            List of dicts with 'word', 'jyutping', 'english', 'added_date' keys
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if limit:
                cursor = await db.execute(
                    """
                    SELECT word, jyutping, english, added_date, review_count
                    FROM vocabulary
                    ORDER BY added_date DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT word, jyutping, english, added_date, review_count
                    FROM vocabulary
                    ORDER BY added_date DESC
                    """
                )

            rows = await cursor.fetchall()

        words: list[dict[str, str]] = []
        for row in rows:
            words.append({
                "word": row["word"],
                "jyutping": row["jyutping"] or "",
                "english": row["english"] or "",
                "added_date": row["added_date"],
                "review_count": str(row["review_count"])
            })

        logger.debug(f"Retrieved {len(words)} vocabulary words")
        return words

    async def update_vocabulary_review(self, word: str) -> None:
        """
        Update the review count and last reviewed date for a vocabulary word.

        Args:
            word: Cantonese word to mark as reviewed
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE vocabulary
                SET review_count = review_count + 1,
                    last_reviewed = CURRENT_TIMESTAMP
                WHERE word = ?
                """,
                (word,)
            )
            await db.commit()

        logger.debug(f"Updated review for word: {word}")
