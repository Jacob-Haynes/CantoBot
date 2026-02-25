# Ollama Local Model Setup Guide

This guide explains how to run CantoBot with a local Qwen3 8B model via Ollama on Raspberry Pi 5.

## Benefits of Local Models

- **No API costs**: All processing runs locally
- **Privacy**: Your conversations never leave your device
- **Offline capability**: Works without internet (after initial setup)
- **Low latency**: No network round-trips to cloud APIs

## Requirements

- Raspberry Pi 5 with 8GB RAM (recommended)
- 10GB+ free disk space
- Debian/Ubuntu-based OS (Raspberry Pi OS recommended)

## Installation

### 1. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Verify installation:
```bash
ollama --version
```

### 2. Pull the Qwen3 8B Model

The 4-bit quantized version fits in ~5GB RAM:

```bash
ollama pull qwen3:8b-q4_K_M
```

This downloads approximately 5GB. Wait for completion.

Test the model:
```bash
ollama run qwen3:8b-q4_K_M "Hello, how are you?"
```

### 3. Install faster-whisper (for Voice Messages)

If you want voice message support:

```bash
pip install faster-whisper
```

Note: First transcription will download the Whisper model (~150MB for base).

### 4. Configure CantoBot

Add these to your `.env` file:

```bash
# Switch to local Ollama backend
MODEL_BACKEND=ollama

# Ollama settings
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:8b-q4_K_M

# Voice transcription (optional)
ENABLE_VOICE=true
WHISPER_MODEL=base

# Keep your other settings
TELEGRAM_BOT_TOKEN=your_token
ALLOWED_USER_ID=your_id
```

### 5. Start the Bot

```bash
python -m src.main
```

## Resource Usage (Pi 5 8GB)

| Component | RAM Usage |
|-----------|-----------|
| Qwen3 8B Q4 | ~5GB |
| Whisper base | ~300MB |
| Bot + Python | ~200MB |
| System | ~900MB |
| **Total** | ~6.4GB |

Leaves ~1.6GB headroom for other processes.

## Verification

### Check Ollama is Running

```bash
curl http://localhost:11434/api/tags
```

Should return JSON with available models.

### Test Model Directly

```bash
ollama run qwen3:8b-q4_K_M "Translate 'hello' to Cantonese"
```

### Check Bot Logs

```bash
# If running with systemd
sudo journalctl -u cantonese_bot -f

# Or check for Ollama handler initialization
LOG_LEVEL=DEBUG python -m src.main
```

Look for:
```
Ollama handler initialized: qwen3:8b-q4_K_M at http://localhost:11434
```

## Switching Back to Gemini

To revert to Google Gemini API:

```bash
# In .env, change:
MODEL_BACKEND=gemini

# Make sure you have:
GOOGLE_API_KEY=your_api_key
```

Or simply remove `MODEL_BACKEND` (defaults to gemini).

## Troubleshooting

### "Connection refused" errors

Ollama service not running:
```bash
sudo systemctl start ollama
sudo systemctl enable ollama  # Auto-start on boot
```

### Out of memory

Try a smaller model:
```bash
ollama pull qwen3:4b-q4_K_M
# Then update OLLAMA_MODEL=qwen3:4b-q4_K_M
```

Or disable voice (saves ~300MB):
```bash
ENABLE_VOICE=false
```

### Slow responses

Expected on Pi 5. Typical response times:
- First token: 2-5 seconds
- Full response: 10-30 seconds

For faster responses, consider:
- Using a smaller model
- Reducing `max_output_tokens` in config
- Running on more powerful hardware

### Whisper model download fails

Manually download:
```bash
python -c "from faster_whisper import WhisperModel; WhisperModel('base')"
```

### Tool calls not working

Qwen3 has native function calling support. If tools aren't triggering:
1. Check logs for "Tool called:" messages
2. Verify tool format in `ollama_handler.py`
3. Test with explicit requests: "Add 早晨 to my vocabulary list"

## Alternative Models

Other models that work well on Pi 5:

| Model | Size | Command |
|-------|------|---------|
| Qwen3 4B | ~2.5GB | `ollama pull qwen3:4b-q4_K_M` |
| Qwen3 8B | ~5GB | `ollama pull qwen3:8b-q4_K_M` |
| Llama 3.2 3B | ~2GB | `ollama pull llama3.2:3b` |
| Phi-3 mini | ~2.3GB | `ollama pull phi3:mini` |

Update `OLLAMA_MODEL` in `.env` to use different models.

## Systemd Service for Ollama

Ollama typically installs its own systemd service. Verify:

```bash
sudo systemctl status ollama
```

If not present, create `/etc/systemd/system/ollama.service`:

```ini
[Unit]
Description=Ollama Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/ollama serve
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
```
