# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CantoBot is a persistent Telegram bot that serves as an AI Cantonese language tutor. It runs on Raspberry Pi 5 and provides voice-to-voice learning using Google Gemini (configurable model) for conversation/transcription and Edge TTS for Cantonese speech synthesis.

**Key Features:**
- Voice and text message handling via Telegram
- Audio transcription and response generation via Gemini
- **Autonomous tool calling**: Dictionary lookup, pronunciation checking, vocabulary management
- Cantonese text-to-speech using Edge TTS (zh-HK-HiuGaaiNeural voice)
- Persistent conversation history, user facts, and vocabulary in SQLite
- Single-user authorization (configured via ALLOWED_USER_ID)

## Development Commands

### Running the Bot

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the bot (development) - must use module syntax
python -m src.main

# Run with DEBUG logging
LOG_LEVEL=DEBUG python -m src.main
```

### Testing Components

```bash
# Test migration and tools (without Telegram)
python test_migration.py

# Test database initialization
python -c "from src.database import DatabaseManager; import asyncio; asyncio.run(DatabaseManager('data/test.db').initialize_db())"

# Test TTS generation
python -c "from src.tts_handler import TTSHandler; import asyncio; asyncio.run(TTSHandler().generate_speech('你好', 'temp/test.mp3'))"

# Test dictionary tools
python -c "from src.tools import cantonese_dictionary; print(cantonese_dictionary('你好'))"

# Test vocabulary database
python -c "from src.tools import add_to_vocabulary, get_vocabulary_list; add_to_vocabulary('早晨'); print(get_vocabulary_list())"
```

### Automated Deployment (Raspberry Pi)

```bash
# Deploy latest code and restart service
./deploy.sh

# This script will:
# - Pull latest code from git
# - Update dependencies in virtual environment
# - Restart the systemd service
# - Verify deployment with health check
```

### Service Management (Raspberry Pi)

```bash
# Start/stop/restart the systemd service
sudo systemctl start cantonese_bot
sudo systemctl stop cantonese_bot
sudo systemctl restart cantonese_bot

# View logs
sudo journalctl -u cantonese_bot -f
sudo journalctl -u cantonese_bot -n 100
```

### Health Check

```bash
# Check bot health (default port 8080)
curl http://localhost:8080/health

# Response format:
# {
#   "status": "ok",
#   "healthy": true,
#   "database": "ok"
# }
```

### Database Queries

```bash
# Count total conversations
sqlite3 data/cantonese_tutor.db "SELECT COUNT(*) FROM conversations;"

# View last 10 interactions
sqlite3 data/cantonese_tutor.db "SELECT timestamp, role, media_type FROM conversations ORDER BY id DESC LIMIT 10;"

# View user facts
sqlite3 data/cantonese_tutor.db "SELECT * FROM user_facts;"

# View vocabulary list
sqlite3 data/cantonese_tutor.db "SELECT word, jyutping, added_date FROM vocabulary ORDER BY added_date DESC;"

# Count vocabulary words
sqlite3 data/cantonese_tutor.db "SELECT COUNT(*) FROM vocabulary;"
```

## Architecture

### Component Overview

The bot follows a modular architecture with clear separation of concerns:

```
main.py (CantoneseBot class)
    ├── config.py (Config) - Environment variable loading
    ├── database.py (DatabaseManager) - SQLite persistence
    ├── gemini_handler.py (GeminiHandler) - AI conversation + tool calling
    ├── tts_handler.py (TTSHandler) - Cantonese speech synthesis
    ├── tools.py (Tool Functions) - Autonomous dictionary/vocabulary tools
    └── health_check.py (HealthCheckServer) - HTTP health endpoint
```

### Request Flow

**Text Messages:**
1. Telegram message received → `handle_text()` in main.py
2. Fetch conversation history and user facts from SQLite
3. Build system prompt with user context
4. Send to Gemini with conversation history and tools
5. **Gemini autonomously calls tools if needed** (dictionary lookup, vocabulary save, etc.)
6. Execute tool functions and send results back to Gemini
7. Save user message and AI response to database
8. Extract Cantonese text and generate TTS audio
9. Reply with text + voice message to Telegram
10. Cleanup temp files

**Voice Messages:**
1. Telegram voice received → `handle_voice()` in main.py
2. Download voice file to `temp/` directory
3. Upload to Gemini for transcription + response (multimodal)
4. **Tool calling works same as text messages**
5. Save conversation to database
6. Generate TTS response from AI text
7. Reply with text + voice message
8. Cleanup temp files and uploaded Gemini file

### Autonomous Tool Calling System

**How it works:**
- Tools are defined in `src/tools.py` as Python functions with docstrings
- Functions passed to Gemini via `GenerateContentConfig(tools=...)`
- Gemini autonomously decides when to call tools based on conversation context
- No manual intent parsing or command detection needed

**Example:**
```
User: "Add 早晨 to my vocabulary list"
→ Gemini calls: add_to_vocabulary("早晨")
→ Tool auto-fills jyutping, saves to database
→ Returns: "Added '早晨' (zou2san4) to your vocabulary list"
→ Gemini incorporates into response: "好！Added 早晨 to your list..."
```

**Available Tools (4):**
1. `add_to_vocabulary(word, jyutping)` - Saves words to vocabulary table
2. `get_vocabulary_list()` - Retrieves saved vocabulary from database
3. `cantonese_dictionary(word)` - PyCantonese jyutping lookup
4. `check_pronunciation(cantonese, user_jyutping)` - Validates pronunciation

### Key Design Patterns

**Authorization:**
- `authorized_only()` decorator in main.py restricts all handlers to ALLOWED_USER_ID
- Unauthorized attempts are logged but receive no response

**Conversation Memory:**
- DatabaseManager stores all messages with role ('user' or 'model'), content, media_type
- `get_recent_history()` retrieves last 20 messages (configurable via CONVERSATION_HISTORY_LIMIT)
- History formatted and injected into Gemini chat context for continuity

**User Facts System:**
- User profile stored in `user_facts` table (key-value pairs)
- Default facts: user_name, user_role, moving_to, moving_date
- Facts interpolated into system prompt template for personalization
- Facts can be updated via `update_user_fact()` (not exposed to user yet)

**Vocabulary Management:**
- Separate `vocabulary` table with UNIQUE constraint on words
- Auto-fills Jyutping using PyCantonese if not provided by user
- Tracks review_count and last_reviewed for future spaced repetition
- Tools use `asyncio.run()` to call async database methods from sync functions

**Error Handling:**
- Retry logic with exponential backoff in Gemini handler (3 attempts)
- TTS failures degrade gracefully (text-only response)
- Temp file cleanup in finally blocks
- All errors logged and generic error messages sent to user
- Tool failures return graceful fallback messages

**Response Format:**
- Gemini instructed to return: `[Cantonese] ([Jyutping])\n[English]`
- TTS extracts only Cantonese characters using regex (CANTONESE_TEXT_PATTERN)
- Example: "做得好！(zou6 dak1 hou2!)\nWell done!" → TTS speaks "做得好！"

## Configuration

Environment variables loaded from `.env`:
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather
- `GOOGLE_API_KEY` - Gemini API key from https://aistudio.google.com/apikey
- `GEMINI_MODEL` - Model selection (default: gemini-2.0-flash-exp)
  - Options: `gemini-1.5-flash`, `gemini-2.0-flash-exp`, `gemini-2.5-flash`
- `ALLOWED_USER_ID` - Single Telegram user ID authorized to use bot
- `DB_PATH` - SQLite database path (default: data/cantonese_tutor.db)
- `LOG_LEVEL` - Logging verbosity: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `HEALTH_CHECK_PORT` - HTTP port for health check endpoint (default: 8080)

## Database Schema

**conversations table:**
- id (INTEGER PRIMARY KEY)
- timestamp (DATETIME)
- role (TEXT) - 'user' or 'model'
- content (TEXT) - Message content or "[voice message]" placeholder
- media_type (TEXT) - 'text' or 'audio'

**user_facts table:**
- key (TEXT PRIMARY KEY)
- value (TEXT)
- updated_at (DATETIME)

**vocabulary table:**
- id (INTEGER PRIMARY KEY)
- word (TEXT UNIQUE) - Cantonese characters
- jyutping (TEXT) - Pronunciation (auto-filled if not provided)
- english (TEXT) - English translation (future enhancement)
- added_date (DATETIME)
- review_count (INTEGER) - For spaced repetition tracking
- last_reviewed (DATETIME) - For spaced repetition

## Gemini API Integration

**Package:** `google-genai` v1.60.0+ (migrated from deprecated `google-generativeai`)

**API Structure:**
```python
from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model=model_name,
    contents=[types.Content(...)],
    config=types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=2048,
        safety_settings=[...],
        tools=[...]  # Tools go inside config, not as separate parameter
    )
)
```

**Key Points:**
- Model name configurable via `GEMINI_MODEL` env var
- Supports multimodal input (text + audio)
- Audio files uploaded via `client.files.upload()`, wait for processing state
- Files deleted after response generation via `client.files.delete()`
- Safety settings: BLOCK_ONLY_HIGH for all categories using `types.HarmCategory` enums
- Tools passed inside `GenerateContentConfig`, not as separate parameter

**Function Calling Flow:**
1. Check response for `function_call` parts
2. Execute function from `AVAILABLE_TOOLS` list
3. Create `types.Part(function_response=...)` with result
4. Send back to Gemini to continue conversation
5. Extract final text response

**System Prompt:**
- Injected as first user message in conversation
- Personalized with user facts (name, role, moving context)
- Instructs "Sifu" persona: strict but encouraging tutor
- Mandates response format with Cantonese, Jyutping, English
- Lists available tools for autonomous use

## PyCantonese Integration

**Library:** `pycantonese>=3.4.0`

**Key Features:**
- 53,000+ word dictionary with Jyutping pronunciations
- Character-to-Jyutping conversion (returns list of tuples)
- Used for dictionary lookup and pronunciation validation

**Important:**
- `characters_to_jyutping()` returns `[(char, jyutping), ...]` tuples, not strings
- Must extract second element: `[jp[1] if isinstance(jp, tuple) else jp for jp in results]`
- Requires `setuptools` for `pkg_resources` compatibility

## Edge TTS Integration

**Voice:** zh-HK-HiuGaaiNeural (female voice, alternative: zh-HK-WanLungNeural)
- Text preprocessed to extract only Cantonese characters
- Removes Jyutping romanization and English translations via regex
- Output saved to temp/ directory as MP3
- Files cleaned up immediately after sending to Telegram

## File Organization

- `src/` - All Python source code
  - `main.py` - Bot entry point and orchestration
  - `config.py` - Environment configuration loader
  - `database.py` - SQLite database manager
  - `gemini_handler.py` - Google Gemini API integration
  - `tts_handler.py` - Edge TTS voice synthesis
  - `tools.py` - Autonomous tool functions (NEW)
  - `health_check.py` - HTTP health check server
  - `prompts.py` - System prompts and constants
- `data/` - SQLite database (created automatically, gitignored)
- `temp/` - Temporary audio files (auto-cleanup, gitignored)
- `test_migration.py` - Test script for Gemini integration without Telegram
- `cantonese_bot.service` - Systemd service definition for Raspberry Pi deployment
- `deploy.sh` - Automated deployment script for Raspberry Pi
- `MIGRATION_SUMMARY.md` - Google-genai migration documentation
- `DICTIONARY_IMPLEMENTATION.md` - Dictionary tool implementation details
- `VOCABULARY_DATABASE.md` - Vocabulary database implementation details

## Important Notes

- Python 3.11+ required (project uses Python 3.13)
- All async code uses asyncio throughout
- Single-threaded event loop (no concurrency issues)
- **Must run as module**: Use `python -m src.main`, not `python src/main.py` (relative imports)
- Temp files must be cleaned up to avoid disk space issues on Raspberry Pi
- Database uses WAL mode for better concurrent access
- Logging level configurable via LOG_LEVEL environment variable
- Health check endpoint runs on separate thread, always available even if bot crashes
- Type hints added throughout codebase for better IDE support and type checking
- Deploy script automates the entire deployment process on Raspberry Pi

## Tool Development Guidelines

When adding new tools to `src/tools.py`:

1. **Function signature**: Clear parameters with type hints
2. **Docstring**: Detailed description with example trigger phrases (Gemini uses this!)
3. **Error handling**: Graceful fallbacks, never crash
4. **Async handling**: Use `asyncio.run()` if calling async database methods
5. **Import placement**: Import DatabaseManager inside function to avoid circular dependencies
6. **Return format**: Clear, concise string that Gemini can incorporate into response
7. **Logging**: Log tool calls and important events for debugging

**Example tool structure:**
```python
def example_tool(param: str) -> str:
    """
    Brief description of what this tool does.

    This tool is called autonomously when user says:
    - "Example trigger phrase"
    - "Another example"

    Args:
        param: Description of parameter

    Returns:
        Result message to incorporate into Sifu's response
    """
    logger.info(f"Tool called: example_tool(param={param})")

    try:
        # Tool logic here
        return f"Success message with {param}"
    except Exception as e:
        logger.error(f"Tool failed: {e}")
        return "Graceful fallback message"
```

## Testing in Development

**Geographic Restrictions:**
- Gemini API may not be available in all regions
- VPN/corporate networks may block SSL connections
- Use `test_migration.py` to test Gemini integration without Telegram

**Testing without Gemini:**
- All components (database, TTS, tools) can be tested independently
- See "Testing Components" section for individual component tests

**Full end-to-end testing:**
- Requires valid credentials in `.env`
- Requires supported geographic region or VPN
- Run `python -m src.main` and test via Telegram
