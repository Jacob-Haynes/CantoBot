"""Tool functions for Gemini autonomous function calling.

The model will AUTONOMOUSLY decide when to call these tools based on natural
language conversation. You don't need to explicitly invoke them - Gemini will
call them when the conversation suggests it.
"""

import logging
from typing import Optional
import httpx
import pycantonese
import asyncio
import os

logger = logging.getLogger(__name__)

# Get database path from environment or use default
DB_PATH = os.getenv("DB_PATH", "data/cantonese_tutor.db")


def add_to_vocabulary(word: str, jyutping: Optional[str] = None) -> str:
    """
    Add a Cantonese word to the user's vocabulary learning list.

    This tool is called autonomously when the user wants to save a word for later,
    such as:
    - "Add that word to my list"
    - "Save this for later"
    - "That was hard, I want to review it"
    - "早晨 was difficult, add it to my list"

    Args:
        word: Cantonese word to add (characters)
        jyutping: Optional Jyutping pronunciation

    Returns:
        Confirmation message that will be incorporated into Sifu's response
    """
    logger.info(f"Tool called: add_to_vocabulary(word={word}, jyutping={jyutping})")

    # Import here to avoid circular dependency
    from .database import DatabaseManager

    async def _add_word():
        db = DatabaseManager(DB_PATH)
        # If jyutping not provided, try to get it from PyCantonese
        jp = jyutping
        if not jp:
            try:
                jyutping_results = pycantonese.characters_to_jyutping(word)
                if jyutping_results:
                    jyutping_list = [j[1] if isinstance(j, tuple) else j for j in jyutping_results]
                    jp = ' '.join(jyutping_list)
            except Exception as e:
                logger.warning(f"Could not get jyutping for {word}: {e}")

        was_added = await db.add_vocabulary_word(word, jp, None)
        return was_added, jp

    try:
        # Run async database operation
        was_added, final_jyutping = asyncio.run(_add_word())

        if was_added:
            if final_jyutping:
                return f"Added '{word}' ({final_jyutping}) to your vocabulary list for review."
            else:
                return f"Added '{word}' to your vocabulary list for review."
        else:
            return f"'{word}' is already in your vocabulary list!"

    except Exception as e:
        logger.error(f"Failed to add vocabulary word: {e}")
        return f"Sorry, I couldn't add '{word}' to your list right now. I'll help you remember it anyway!"


def get_vocabulary_list() -> str:
    """
    Get the user's saved vocabulary words.

    This tool is called autonomously when the user asks about their list:
    - "What's on my list?"
    - "Show me my vocabulary"
    - "What words am I learning?"
    - "What have I saved?"

    Returns:
        List of vocabulary words with pronunciations
    """
    logger.info("Tool called: get_vocabulary_list()")

    # Import here to avoid circular dependency
    from .database import DatabaseManager

    async def _get_words():
        db = DatabaseManager(DB_PATH)
        return await db.get_vocabulary_words()

    try:
        words = asyncio.run(_get_words())

        if not words:
            return "Your vocabulary list is empty. Ask me to add words as you learn!"

        # Format the list nicely
        formatted_words = []
        for i, word_data in enumerate(words, 1):
            word = word_data["word"]
            jyutping = word_data["jyutping"]
            if jyutping:
                formatted_words.append(f"{i}. {word} ({jyutping})")
            else:
                formatted_words.append(f"{i}. {word}")

        result = "Your vocabulary list:\n" + "\n".join(formatted_words)

        # Add count summary
        total = len(words)
        result += f"\n\nTotal: {total} word{'s' if total != 1 else ''}"

        return result

    except Exception as e:
        logger.error(f"Failed to get vocabulary list: {e}")
        return "Sorry, I couldn't retrieve your vocabulary list right now."


def check_pronunciation(cantonese: str, user_jyutping: str) -> str:
    """
    Validate user's Jyutping romanization against correct pronunciation.

    This tool is called autonomously when the user attempts to provide
    pronunciation or when checking their understanding:
    - "Is it zou6 san4?"
    - "How do you pronounce 早晨?"
    - User provides Jyutping in their message

    Args:
        cantonese: Cantonese characters
        user_jyutping: User's attempt at Jyutping

    Returns:
        Feedback on pronunciation accuracy
    """
    logger.info(f"Tool called: check_pronunciation(cantonese={cantonese}, user_jyutping={user_jyutping})")

    try:
        # Get correct pronunciation using PyCantonese
        jyutping_results = pycantonese.characters_to_jyutping(cantonese)

        # PyCantonese returns list of tuples: [(char, jyutping), ...]
        # Extract just the jyutping strings
        jyutping_list = [jp[1] if isinstance(jp, tuple) else jp for jp in jyutping_results]
        correct_jyutping = ' '.join(jyutping_list)

        # Normalize both for comparison (remove spaces, lowercase)
        user_normalized = user_jyutping.replace(' ', '').lower().strip()
        correct_normalized = correct_jyutping.replace(' ', '').lower().strip()

        logger.info(f"Comparing: user='{user_normalized}' vs correct='{correct_normalized}'")

        if user_normalized == correct_normalized:
            return f"✓ Correct! '{cantonese}' is pronounced {correct_jyutping}"
        else:
            return f"Not quite. '{cantonese}' is pronounced {correct_jyutping}, not {user_jyutping}"

    except Exception as e:
        logger.error(f"Pronunciation check failed: {e}")
        return f"Could not verify pronunciation for '{cantonese}'. Let me help you learn it correctly instead."


def cantonese_dictionary(word: str) -> str:
    """
    Look up Cantonese word definition and pronunciation.

    This tool is called autonomously when the user asks about word meanings:
    - "What does 早晨 mean?"
    - "How do you say good morning?"
    - "Define 你好"
    - "Tell me about the word 茶"

    Args:
        word: Cantonese word to look up (characters)

    Returns:
        Definition with Jyutping and English translation
    """
    logger.info(f"Tool called: cantonese_dictionary(word={word})")

    result_parts = []

    # Step 1: Get Jyutping pronunciation using PyCantonese
    try:
        jyutping_results = pycantonese.characters_to_jyutping(word)
        if jyutping_results:
            # PyCantonese returns list of tuples: [(char, jyutping), ...]
            # Extract just the jyutping strings
            jyutping_list = [jp[1] if isinstance(jp, tuple) else jp for jp in jyutping_results]
            jyutping_str = ' '.join(jyutping_list)
            result_parts.append(f"Pronunciation: {jyutping_str}")
            logger.info(f"PyCantonese jyutping: {jyutping_str}")
    except Exception as e:
        logger.warning(f"PyCantonese lookup failed: {e}")

    # Step 2: Try to get definition from CC-Canto via cantonese.org
    try:
        with httpx.Client(timeout=5.0) as client:
            # SearchCanto provides a search interface we can use
            response = client.get(
                "https://searchcanto.com/api/search",
                params={"q": word, "type": "cantonese"}
            )

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    first_result = data[0]
                    english = first_result.get('english', '')
                    if english:
                        result_parts.append(f"English: {english}")
                        logger.info(f"Found definition: {english}")
    except Exception as e:
        logger.warning(f"Online dictionary lookup failed: {e}")
        # Don't fail the whole lookup if web request fails

    # Step 3: Format and return result
    if result_parts:
        formatted = f"'{word}' - " + " | ".join(result_parts)
        return formatted
    else:
        # Fallback if both lookups fail
        return f"'{word}' - Could not find detailed dictionary entry. The word might be uncommon or spelled differently. Sifu can still help you learn it!"


# List of tools to expose to Gemini
# The model will AUTONOMOUSLY decide when to call these based on conversation
AVAILABLE_TOOLS = [
    add_to_vocabulary,      # Save words to learning list
    get_vocabulary_list,    # Retrieve saved words
    check_pronunciation,    # Validate Jyutping
    cantonese_dictionary    # Look up word definitions
]
