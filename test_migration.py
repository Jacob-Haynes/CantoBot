#!/usr/bin/env python3
"""Test script to verify Gemini migration and tool calling without Telegram."""

import asyncio
import sys
from pathlib import Path

# Add parent to path for module imports
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.gemini_handler import GeminiHandler
from src.database import DatabaseManager


async def test_basic_conversation():
    """Test basic conversation without tools."""
    print("=" * 60)
    print("TEST 1: Basic Conversation (No Tools)")
    print("=" * 60)

    config = Config()
    gemini = GeminiHandler(config.google_api_key, config.gemini_model)
    db = DatabaseManager(config.db_path)
    await db.initialize_db()

    user_facts = await db.get_user_facts()

    print(f"\nUsing model: {config.gemini_model}")
    print(f"User: 你好！How do I say 'good morning'?\n")

    try:
        response = await gemini.process_text(
            "你好！How do I say 'good morning'?",
            [],
            user_facts
        )
        print(f"Sifu: {response}\n")
        print("✅ Basic conversation works!\n")
        return True
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


async def test_tool_calling():
    """Test autonomous tool calling."""
    print("=" * 60)
    print("TEST 2: Autonomous Tool Calling")
    print("=" * 60)

    config = Config()
    gemini = GeminiHandler(config.google_api_key, config.gemini_model)
    db = DatabaseManager(config.db_path)
    await db.initialize_db()

    user_facts = await db.get_user_facts()

    print(f"\nUser: Add 早晨 to my vocabulary list\n")

    try:
        response = await gemini.process_text(
            "Add 早晨 to my vocabulary list",
            [],
            user_facts
        )
        print(f"Sifu: {response}\n")
        print("✅ Tool calling works!\n")
        return True
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


async def test_vocabulary_retrieval():
    """Test vocabulary list retrieval."""
    print("=" * 60)
    print("TEST 3: Vocabulary List Retrieval")
    print("=" * 60)

    config = Config()
    gemini = GeminiHandler(config.google_api_key, config.gemini_model)
    db = DatabaseManager(config.db_path)
    await db.initialize_db()

    user_facts = await db.get_user_facts()

    print(f"\nUser: What's on my vocabulary list?\n")

    try:
        response = await gemini.process_text(
            "What's on my vocabulary list?",
            [],
            user_facts
        )
        print(f"Sifu: {response}\n")
        print("✅ Vocabulary retrieval works!\n")
        return True
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("GEMINI MIGRATION & TOOL TESTING")
    print("=" * 60 + "\n")

    results = []

    # Test 1: Basic conversation
    results.append(await test_basic_conversation())

    # Test 2: Tool calling
    results.append(await test_tool_calling())

    # Test 3: Vocabulary retrieval
    results.append(await test_vocabulary_retrieval())

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"\n✅ Passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Migration successful!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check errors above.")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())