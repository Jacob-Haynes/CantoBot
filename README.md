# Cantonese AI Tutor Bot

A persistent, always-on AI Cantonese tutor running on Raspberry Pi 5 with voice-to-voice capabilities, autonomous tool calling, and persistent memory.

**Supports two AI backends:**
- **Google Gemini** (cloud) - Default, multimodal with built-in audio transcription
- **Ollama** (local) - Run Qwen3 8B locally on Pi 5 for privacy and offline use 

## Features

### Core Capabilities
- 🎤 **Voice-to-Voice Learning**: Send voice messages in Cantonese, receive spoken feedback
- 💬 **Text Interaction**: Practice with text messages and get corrections
- 🧠 **Persistent Memory**: Conversation history and user context stored in SQLite
- 🎯 **Personalized Tutoring**: Learns your common mistakes and adapts to your learning journey
- 📱 **24/7 Availability**: Always-on service on Raspberry Pi

### Autonomous Tool System (NEW)
The bot autonomously decides when to use these tools based on natural conversation:

- **📚 Dictionary Lookup**: "What does 早晨 mean?" → Automatic Jyutping and pronunciation
- **✅ Pronunciation Check**: "Is it zou6 san4?" → Validates your pronunciation attempts
- **📝 Vocabulary Management**: "Add that to my list" → Saves words to review database
- **📊 Vocabulary List**: "What's on my list?" → Retrieves saved words with pronunciations

**No commands needed** - the bot understands natural language and calls tools automatically!

## Architecture

```
┌─────────────┐
│  Telegram   │
│    User     │
└──────┬──────┘
       │ Voice/Text
       ▼
┌─────────────────────────────────────────┐
│         Raspberry Pi 5                  │
│  ┌───────────────────────────────────┐  │
│  │  Cantonese Bot (Python)           │  │
│  │  ├─ Telegram Bot Handler          │  │
│  │  ├─ AI Backend (configurable)     │  │
│  │  │  ├─ Google Gemini (cloud)      │  │
│  │  │  │  - Multimodal transcription │  │
│  │  │  └─ Ollama + Whisper (local)   │  │
│  │  │     - Qwen3 8B + faster-whisper│  │
│  │  ├─ Autonomous Tool Calling       │  │
│  │  ├─ PyCantonese (Dictionary)      │  │
│  │  ├─ Edge TTS (Text → Cantonese)   │  │
│  │  └─ SQLite Database               │  │
│  │     - Conversations                │  │
│  │     - User Facts                   │  │
│  │     - Vocabulary List              │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Technology Stack

- **AI Backend** (configurable):
  - Google Gemini (cloud): 1.5-flash, 2.0-flash-exp, 2.5-flash
  - Ollama (local): Qwen3 8B, Llama 3.2, Phi-3, etc.
- **Audio Transcription**:
  - Gemini: Built-in multimodal
  - Ollama: faster-whisper (local)
- **NLP Library**: PyCantonese (53k+ word dictionary with Jyutping)
- **TTS**: Edge TTS (zh-HK-HiuGaaiNeural voice)
- **Database**: SQLite with WAL mode
- **Framework**: python-telegram-bot v21+
- **Language**: Python 3.11+ (tested on 3.13)

## Quick Start

### Prerequisites

- **Hardware**: Raspberry Pi 5 (4GB+ RAM) with 16GB+ SD card
- **OS**: Raspberry Pi OS with Python 3.11+
- **Internet**: Stable broadband connection
- **Accounts**: Telegram Bot Token, Google Gemini API Key

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/CantoBot.git
cd CantoBot

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your API keys
```

### Configuration

Edit `.env` with your credentials:

```env
# Get from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Your Telegram user ID (message @userinfobot to find it)
ALLOWED_USER_ID=your_telegram_user_id_here

# --- Backend Selection (choose one) ---

# Option 1: Google Gemini (default, cloud-based)
MODEL_BACKEND=gemini
GOOGLE_API_KEY=your_google_api_key_here  # Get from https://aistudio.google.com/apikey
GEMINI_MODEL=gemini-2.0-flash-exp        # Options: gemini-1.5-flash, gemini-2.0-flash-exp, gemini-2.5-flash

# Option 2: Ollama (local, runs on Pi 5)
# MODEL_BACKEND=ollama
# OLLAMA_HOST=http://localhost:11434
# OLLAMA_MODEL=qwen3:8b-q4_K_M
# WHISPER_MODEL=base                     # For voice transcription: tiny, base, small
# ENABLE_VOICE=true                      # Set to false to disable voice messages

# --- General Settings ---
DB_PATH=data/cantonese_tutor.db
LOG_LEVEL=INFO
HEALTH_CHECK_PORT=8080
```

See [docs/OLLAMA_SETUP.md](docs/OLLAMA_SETUP.md) for detailed local model setup instructions.

### Run

```bash
# Development mode
source .venv/bin/activate
python -m src.main

# With debug logging
LOG_LEVEL=DEBUG python -m src.main
```

## Production Deployment (Raspberry Pi)

### Set Up as Systemd Service

```bash
# Install service
sudo cp cantonese_bot.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable cantonese_bot

# Start service
sudo systemctl start cantonese_bot

# Check status
sudo systemctl status cantonese_bot
```

### Automated Deployment

Use the deployment script for updates:

```bash
./deploy.sh
```

This will:
1. Pull latest code from git
2. Update dependencies in virtual environment
3. Restart the systemd service
4. Verify deployment with health check

### Service Management

```bash
# View logs
sudo journalctl -u cantonese_bot -f

# Restart service
sudo systemctl restart cantonese_bot

# Stop service
sudo systemctl stop cantonese_bot
```

## Usage Guide

### Starting a Conversation

1. Open Telegram and find your bot
2. Send `/start` to initialize
3. Send a text or voice message in Cantonese

### Response Format

```
做得好！(zou6 dak1 hou2!)
Well done!
[+ voice message with Cantonese pronunciation]
```

- **First line**: Cantonese characters with Jyutping romanization
- **Second line**: English translation
- **Voice message**: Audio pronunciation

### Example Interactions

**Dictionary Lookup:**
```
You: What does 早晨 mean?
Bot: [Automatically calls dictionary tool]
     早晨 (zou2 san4) means "good morning"!
     Let me teach you how to use it...
     [+ voice message]
```

**Vocabulary Management:**
```
You: Add 早晨 to my vocabulary list
Bot: [Automatically saves to database]
     好！(hou2!) I've added 早晨 (zou2 san4) to your vocabulary list.
     [+ voice message]

You: What's on my list?
Bot: [Retrieves from database]
     Your vocabulary list:
     1. 早晨 (zou2 san4)
     2. 你好 (nei5 hou2)
     Total: 2 words
```

**Pronunciation Check:**
```
You: Is 早晨 pronounced zou6 san4?
Bot: [Automatically validates]
     Not quite. 早晨 is pronounced zou2 san4, not zou6 san4.
     The first tone should be rising (tone 2), not high level (tone 6).
```

## Database Schema

### Conversations Table
Stores complete message history:

| Column      | Type     | Description                    |
|-------------|----------|--------------------------------|
| id          | INTEGER  | Primary key                    |
| timestamp   | DATETIME | Message timestamp              |
| role        | TEXT     | 'user' or 'model'              |
| content     | TEXT     | Message content                |
| media_type  | TEXT     | 'text' or 'audio'              |

### User Facts Table
Stores learner profile for personalization:

| Column      | Type     | Description                    |
|-------------|----------|--------------------------------|
| key         | TEXT     | Fact key (primary key)         |
| value       | TEXT     | Fact value                     |
| updated_at  | DATETIME | Last update timestamp          |

Default facts: `user_name`, `user_role`, `moving_to`, `moving_date`

### Vocabulary Table (NEW)
Stores saved words for review:

| Column        | Type     | Description                    |
|---------------|----------|--------------------------------|
| id            | INTEGER  | Primary key                    |
| word          | TEXT     | Cantonese characters (UNIQUE)  |
| jyutping      | TEXT     | Auto-filled pronunciation      |
| english       | TEXT     | English translation            |
| added_date    | DATETIME | When word was added            |
| review_count  | INTEGER  | Times reviewed (for SRS)       |
| last_reviewed | DATETIME | Last review timestamp          |

### Database Queries

```bash
# View vocabulary
sqlite3 data/cantonese_tutor.db "SELECT word, jyutping, added_date FROM vocabulary ORDER BY added_date DESC;"

# Count conversations
sqlite3 data/cantonese_tutor.db "SELECT COUNT(*) FROM conversations;"

# Recent interactions
sqlite3 data/cantonese_tutor.db "SELECT timestamp, role, media_type FROM conversations ORDER BY id DESC LIMIT 10;"
```

## Technical Details

### Google Gemini API Integration

**Package**: `google-genai` v1.60.0+ (migrated from deprecated `google-generativeai`)

The bot uses the new official Gemini API client:

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
        tools=[...]  # Autonomous tool calling
    )
)
```

**Key Features:**
- Multimodal input (text + audio)
- Autonomous function calling
- Configurable model selection
- File upload for audio transcription
- Built-in retry logic

### Autonomous Tool Calling

Tools are Python functions that Gemini calls automatically based on conversation context:

```python
def add_to_vocabulary(word: str, jyutping: Optional[str] = None) -> str:
    """
    Add a Cantonese word to the user's vocabulary learning list.

    This tool is called autonomously when the user wants to save a word:
    - "Add that word to my list"
    - "Save 早晨 for later"
    """
    # Auto-fill jyutping using PyCantonese if not provided
    # Save to database
    # Return confirmation message
```

**How it works:**
1. User sends message: "Add 早晨 to my list"
2. Gemini detects intent and calls `add_to_vocabulary("早晨")`
3. Tool executes, saves to database, returns confirmation
4. Gemini incorporates result into natural response
5. User receives: "好！Added 早晨 (zou2san4) to your vocabulary list."

**Available Tools:**
- `cantonese_dictionary(word)` - PyCantonese jyutping lookup
- `check_pronunciation(cantonese, user_jyutping)` - Validates pronunciation
- `add_to_vocabulary(word, jyutping)` - Saves to database
- `get_vocabulary_list()` - Retrieves saved words

### PyCantonese Integration

**Library**: PyCantonese 3.4.0+ (53,000+ word dictionary)

Used for:
- Character-to-Jyutping conversion
- Dictionary lookups
- Pronunciation validation

**Important Implementation Detail:**
```python
# PyCantonese returns tuples, not strings
jyutping_results = pycantonese.characters_to_jyutping('你好')
# Returns: [('你', 'nei5'), ('好', 'hou2')]

# Extract jyutping strings
jyutping_list = [jp[1] for jp in jyutping_results]
jyutping_str = ' '.join(jyutping_list)  # 'nei5 hou2'
```

### Edge TTS Integration

**Voice**: zh-HK-HiuGaaiNeural (female Cantonese voice)

Features:
- Neural voice synthesis
- Free to use
- Extracts Cantonese text via regex (removes Jyutping/English)
- MP3 output to `temp/` directory
- Automatic cleanup after sending

### Local Model Support (Ollama)

Run CantoBot entirely locally on Raspberry Pi 5 using Ollama:

**Benefits:**
- No API costs
- Complete privacy (data never leaves device)
- Offline capability
- ~10-30 second response times on Pi 5

**Quick Setup:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model (~5GB download)
ollama pull qwen3:8b-q4_K_M

# Install voice transcription (optional)
pip install faster-whisper

# Configure .env
MODEL_BACKEND=ollama
```

**Resource Usage (Pi 5 8GB):**
| Component | RAM |
|-----------|-----|
| Qwen3 8B Q4 | ~5GB |
| Whisper base | ~300MB |
| Bot + System | ~1.1GB |
| **Total** | ~6.4GB |

See [docs/OLLAMA_SETUP.md](docs/OLLAMA_SETUP.md) for complete setup guide.

## Development

### Project Structure

```
CantoBot/
├── src/
│   ├── main.py              # Bot orchestration + handler factory
│   ├── config.py            # Environment configuration
│   ├── database.py          # SQLite manager
│   ├── gemini_handler.py    # Google Gemini API backend
│   ├── ollama_handler.py    # Ollama local model backend
│   ├── whisper_handler.py   # Local audio transcription
│   ├── tts_handler.py       # Edge TTS synthesis
│   ├── tools.py             # Autonomous tool functions
│   ├── health_check.py      # HTTP health endpoint
│   └── prompts.py           # System prompts
├── docs/
│   └── OLLAMA_SETUP.md      # Local model setup guide
├── data/                    # SQLite database (gitignored)
├── temp/                    # Temp audio files (gitignored)
├── test_migration.py        # Test tools without Telegram
├── cantonese_bot.service    # Systemd service file
├── deploy.sh               # Deployment script
├── requirements.txt        # Python dependencies
├── .env.example            # Config template
└── README.md              # This file
```

### Testing Components

```bash
# Test Gemini integration and tools (no Telegram required)
python test_migration.py

# Test database
python -c "from src.database import DatabaseManager; import asyncio; asyncio.run(DatabaseManager('data/test.db').initialize_db())"

# Test TTS
python -c "from src.tts_handler import TTSHandler; import asyncio; asyncio.run(TTSHandler().generate_speech('你好', 'temp/test.mp3'))"

# Test dictionary
python -c "from src.tools import cantonese_dictionary; print(cantonese_dictionary('你好'))"

# Test vocabulary
python -c "from src.tools import add_to_vocabulary, get_vocabulary_list; add_to_vocabulary('早晨'); print(get_vocabulary_list())"
```

### Adding New Tools

Create a new function in `src/tools.py`:

```python
def my_new_tool(param: str) -> str:
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
    logger.info(f"Tool called: my_new_tool(param={param})")

    try:
        # Tool logic here
        return f"Success message with {param}"
    except Exception as e:
        logger.error(f"Tool failed: {e}")
        return "Graceful fallback message"
```

Then add it to `AVAILABLE_TOOLS` list in the same file.

### Running Tests

The bot includes geographic restrictions awareness:

```bash
# Test without Gemini API (works anywhere)
python -c "from src.tools import cantonese_dictionary; print(cantonese_dictionary('你好'))"

# Test with Gemini (requires supported region or VPN)
python test_migration.py
```

## Monitoring

### System Health

```bash
# Check bot status
sudo systemctl status cantonese_bot

# Health endpoint
curl http://localhost:8080/health

# CPU temperature (Raspberry Pi)
vcgencmd measure_temp

# Memory usage
free -h

# Disk usage
df -h
```

### Bot Metrics

```bash
# Total conversations
sqlite3 data/cantonese_tutor.db "SELECT COUNT(*) FROM conversations;"

# Vocabulary count
sqlite3 data/cantonese_tutor.db "SELECT COUNT(*) FROM vocabulary;"

# Recent activity
sqlite3 data/cantonese_tutor.db "SELECT timestamp, role, media_type FROM conversations ORDER BY id DESC LIMIT 10;"
```

## Troubleshooting

### Bot Not Responding

1. Check service status: `sudo systemctl status cantonese_bot`
2. View logs: `sudo journalctl -u cantonese_bot -n 50`
3. Verify `.env` configuration
4. Check API key validity at https://aistudio.google.com/apikey

### Geographic Restrictions

**Symptom**: `400 FAILED_PRECONDITION` or `User location is not supported`

**Cause**: Gemini API not available in your region

**Solution**:
- Use VPN to supported region (US, UK, etc.)
- Test components independently using test scripts
- Deploy to Raspberry Pi in supported region

### Voice Messages Not Working

1. Check Gemini API quota at https://aistudio.google.com/apikey
2. Verify temp directory permissions: `ls -la temp/`
3. Test TTS manually (see Testing Components section)

### Database Errors

```bash
# Check database file
ls -la data/cantonese_tutor.db

# Reset database (CAUTION: deletes all history)
rm data/cantonese_tutor.db
sudo systemctl restart cantonese_bot
```

### Import Errors

**Always run as module:**
```bash
# ✅ Correct
python -m src.main

# ❌ Wrong (will fail with import errors)
python src/main.py
```

## Migration Notes

This bot recently migrated from `google-generativeai` to `google-genai` (January 2026):

**What Changed:**
- API client initialization: `genai.configure()` → `genai.Client()`
- Model interface: `GenerativeModel.start_chat()` → `client.models.generate_content()`
- Safety settings now use enums: `types.HarmCategory`, `types.HarmBlockThreshold`
- Tools passed inside config: `GenerateContentConfig(tools=...)`
- File uploads: `genai.upload_file()` → `client.files.upload()`

**Benefits:**
- No more deprecation warnings
- Future-proof with official package
- Better type safety
- Autonomous tool calling support

**Compatibility:**
- Python 3.11+ required
- Free tier Gemini API still works
- No data migration needed (database unchanged)

## Security

- **User Filtering**: Only responds to configured `ALLOWED_USER_ID`
- **Logging**: All unauthorized access attempts logged
- **API Keys**: Stored in `.env` (gitignored, never committed)
- **Network**: Bot uses polling (no exposed ports except health check)

## Hardware Requirements

- **Raspberry Pi 5**: 4GB+ RAM (8GB required for local Ollama backend)
- **Storage**: 16GB+ SD card (32GB+ recommended for local models)
- **Network**: Stable broadband (Gemini), or none (Ollama after setup)
- **Power**: Official 27W USB-C power supply
- **OS**: Raspberry Pi OS (Bookworm/Trixie) with Python 3.11+

## Dependencies

See `requirements.txt`:
- `python-telegram-bot[job-queue]>=21.0` - Telegram bot framework
- `google-genai>=1.0.0` - Google Gemini API
- `pycantonese>=3.4.0` - Cantonese NLP library
- `edge-tts>=7.0.0` - Text-to-speech
- `aiosqlite>=0.20.0` - Async SQLite
- `httpx>=0.28.0` - HTTP client (Ollama + dictionary APIs)
- `python-dotenv>=1.0.0` - Environment configuration
- `setuptools>=80.0.0` - PyCantonese compatibility

**Optional (for local Ollama backend):**
- `faster-whisper>=1.0.0` - Local audio transcription

## Contributing

This is a personal project, but suggestions are welcome! Open an issue to discuss improvements.

## License

MIT License - See LICENSE file for details

## Acknowledgments

- **Google Gemini**: Cloud AI for conversation and transcription
- **Ollama**: Local LLM inference engine
- **Qwen3**: Excellent multilingual model from Alibaba
- **faster-whisper**: Efficient local speech recognition
- **PyCantonese**: Open-source Cantonese NLP (Jackson L. Lee)
- **Edge TTS**: Free neural Cantonese voices
- **python-telegram-bot**: Excellent Telegram bot framework
- **Cantonese Learners**: For the motivation to build this

---

**Made with ❤️ for learning Cantonese before moving to Hong Kong**
