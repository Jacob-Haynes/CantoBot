"""System prompts, constants, and message templates for the Cantonese AI Tutor Bot."""

# Gemini Configuration
GEMINI_MODEL_NAME = "gemini-1.5-flash"

# TTS Configuration
TTS_VOICE_NAME = "zh-HK-HiuGaaiNeural"  # Female voice, clear pronunciation
TTS_VOICE_NAME_ALT = "zh-HK-WanLungNeural"  # Male alternative

# System Prompt Template
SYSTEM_PROMPT_TEMPLATE = """You are 'Sifu', a strict but encouraging Cantonese tutor.

Student: {user_name}, {user_role}
Context: Moving to {moving_to} in {moving_date}

AVAILABLE TOOLS (use autonomously when helpful):
- add_to_vocabulary: Save words the student wants to review later
- get_vocabulary_list: Show the student's saved vocabulary
- cantonese_dictionary: Look up word definitions and pronunciations
- check_pronunciation: Validate Jyutping romanization

RESPONSE FORMAT (MANDATORY):
[Cantonese Characters] ([Jyutping Romanization])
[English Translation]

RULES:
- Always correct tonal mistakes explicitly
- Use tools when the student asks to save words, check their list, or needs definitions
- Be encouraging but don't let errors slide
- Track common mistakes and remind the student
- Use real Hong Kong conversational patterns
- Keep responses concise (2-4 sentences max)

Example:
做得好！(zou6 dak1 hou2!)
Well done!
"""

# Welcome Messages
WELCOME_MESSAGE = """歡迎！(fun1 jing4!) Welcome!

I'm Sifu, your Cantonese tutor. I'm here to help you prepare for your move to Hong Kong!

You can:
• Send me voice messages - I'll listen and respond
• Send me text messages - I'll correct and encourage
• Practice real conversational Cantonese

Let's start! Try saying "你好" (nei5 hou2) - Hello!
"""

# Error Messages
ERROR_GENERIC = "抱歉 (pou3 hip3) - Sorry, something went wrong. Please try again."
ERROR_PROCESSING_AUDIO = "I had trouble processing your voice message. Please try again."
ERROR_PROCESSING_TEXT = "I had trouble understanding your message. Please try again."
ERROR_TTS_GENERATION = "I couldn't generate the voice response, but here's the text."
ERROR_UNAUTHORIZED = "Unauthorized access attempt detected."

# Regular Expressions
# Extract Cantonese text before romanization: matches text before parentheses
CANTONESE_TEXT_PATTERN = r'^(.+?)\s*\([^)]+\)'

# Database Configuration
DEFAULT_USER_FACTS = {
    "user_name": "Jacob",
    "user_role": "AI Systems Principal",
    "moving_to": "Hong Kong",
    "moving_date": "2026"
}

# Conversation History
CONVERSATION_HISTORY_LIMIT = 20  # Last 20 messages (10 exchanges)

# File Paths
TEMP_DIR = "temp"
DATA_DIR = "data"
