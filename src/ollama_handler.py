"""Ollama API handler for local AI conversation processing."""

import logging
import asyncio
import json
from typing import Any, Optional

import httpx

from .prompts import SYSTEM_PROMPT_TEMPLATE
from .tools import AVAILABLE_TOOLS

logger = logging.getLogger(__name__)


class OllamaHandler:
    """Handler for Ollama API interactions with local models."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "qwen3:8b-q4_K_M",
        whisper_handler: Optional[Any] = None
    ) -> None:
        """
        Initialize Ollama handler.

        Args:
            host: Ollama API host URL
            model: Model name to use
            whisper_handler: Optional WhisperHandler for audio transcription
        """
        self.host = host.rstrip("/")
        self.model = model
        self.whisper_handler = whisper_handler

        # Convert tools to Ollama format
        self.tools = self._convert_tools_to_ollama_format()

        logger.info(f"Ollama handler initialized: {model} at {host}")
        logger.info(f"Tools enabled: {[tool.__name__ for tool in AVAILABLE_TOOLS]}")
        if whisper_handler:
            logger.info(f"Whisper transcription enabled: {whisper_handler.model_size}")

    def _convert_tools_to_ollama_format(self) -> list[dict[str, Any]]:
        """
        Convert Python functions to Ollama tool format.

        Returns:
            List of tool definitions in Ollama JSON format
        """
        tools = []

        for func in AVAILABLE_TOOLS:
            # Extract function info from type hints and docstring
            import inspect
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or ""

            # Parse parameters
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                param_type = "string"  # Default to string
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == str:
                        param_type = "string"
                    elif param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == bool:
                        param_type = "boolean"
                    elif hasattr(param.annotation, "__origin__"):
                        # Handle Optional[str] etc.
                        param_type = "string"

                properties[param_name] = {
                    "type": param_type,
                    "description": f"Parameter: {param_name}"
                }

                # Required if no default value
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            tool_def = {
                "type": "function",
                "function": {
                    "name": func.__name__,
                    "description": doc.split("\n")[0] if doc else func.__name__,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
            }
            tools.append(tool_def)

        return tools

    def build_system_prompt(self, user_facts: dict[str, str]) -> str:
        """
        Build the system prompt with user facts.

        Args:
            user_facts: Dictionary of user facts from database

        Returns:
            Formatted system prompt
        """
        return SYSTEM_PROMPT_TEMPLATE.format(
            user_name=user_facts.get("user_name", "Student"),
            user_role=user_facts.get("user_role", "Learner"),
            moving_to=user_facts.get("moving_to", "Hong Kong"),
            moving_date=user_facts.get("moving_date", "soon")
        )

    async def _execute_function_call(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a function call requested by the model.

        Args:
            tool_call: Tool call object from Ollama response

        Returns:
            Function response dict with name and result
        """
        func_name: str = tool_call["function"]["name"]
        func_args: dict[str, Any] = tool_call["function"].get("arguments", {})

        # Parse arguments if they're a string
        if isinstance(func_args, str):
            try:
                func_args = json.loads(func_args)
            except json.JSONDecodeError:
                func_args = {}

        logger.info(f"Executing function: {func_name}({func_args})")

        # Find and call the function
        func = next((f for f in AVAILABLE_TOOLS if f.__name__ == func_name), None)
        if func is None:
            error_msg = f"Function {func_name} not found in AVAILABLE_TOOLS"
            logger.error(error_msg)
            return {"name": func_name, "result": error_msg}

        try:
            result: str = func(**func_args)
            logger.info(f"Function {func_name} returned: {result[:100]}")
            return {"name": func_name, "result": result}
        except Exception as e:
            error_msg = f"Error executing {func_name}: {e}"
            logger.error(error_msg)
            return {"name": func_name, "result": error_msg}

    async def _call_ollama(
        self,
        messages: list[dict[str, str]],
        include_tools: bool = True
    ) -> dict[str, Any]:
        """
        Make an async call to the Ollama API.

        Args:
            messages: List of message dicts with role and content
            include_tools: Whether to include tools in the request

        Returns:
            Ollama API response dict
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 2048
            }
        }

        if include_tools and self.tools:
            payload["tools"] = self.tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.host}/api/chat",
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def process_text(
        self,
        text: str,
        conversation_history: list[dict[str, str]],
        user_facts: dict[str, str]
    ) -> str:
        """
        Process a text message and generate a response.

        Args:
            text: User's text message
            conversation_history: Recent conversation history
            user_facts: User facts from database

        Returns:
            AI-generated response text
        """
        system_prompt: str = self.build_system_prompt(user_facts)

        # Build messages list for Ollama
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for msg in conversation_history:
            messages.append({
                "role": msg["role"] if msg["role"] != "model" else "assistant",
                "content": msg["content"]
            })

        # Add current message
        messages.append({"role": "user", "content": text})

        # Generate response with retry logic
        for attempt in range(3):
            try:
                logger.info(f"Sending text request to Ollama (attempt {attempt + 1})")

                response = await self._call_ollama(messages)

                # Handle tool calls if present
                message = response.get("message", {})
                tool_calls = message.get("tool_calls", [])

                if tool_calls:
                    logger.info(f"Model requested {len(tool_calls)} tool call(s)")

                    # Add assistant message with tool calls
                    messages.append(message)

                    # Execute all tool calls
                    for tool_call in tool_calls:
                        func_result = await self._execute_function_call(tool_call)

                        # Add tool response
                        messages.append({
                            "role": "tool",
                            "content": func_result["result"]
                        })

                    # Continue conversation with tool results
                    logger.info("Sending tool results back to model")
                    response = await self._call_ollama(messages, include_tools=False)

                result: str = response.get("message", {}).get("content", "")
                logger.info(f"Received response: {result[:100]}...")
                return result

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error (attempt {attempt + 1}): {e}")
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Error processing text (attempt {attempt + 1}): {e}")
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError("Failed to process text after 3 attempts")

    async def process_audio(
        self,
        audio_path: str,
        conversation_history: list[dict[str, str]],
        user_facts: dict[str, str]
    ) -> str:
        """
        Process an audio file and generate a response.

        Args:
            audio_path: Path to audio file
            conversation_history: Recent conversation history
            user_facts: User facts from database

        Returns:
            AI-generated response text
        """
        if self.whisper_handler is None:
            raise RuntimeError(
                "Voice messages require Whisper transcription. "
                "Set ENABLE_VOICE=true and install faster-whisper."
            )

        # Transcribe audio locally
        logger.info(f"Transcribing audio: {audio_path}")
        transcribed_text = await asyncio.to_thread(
            self.whisper_handler.transcribe,
            audio_path
        )

        logger.info(f"Transcription: {transcribed_text[:100]}...")

        # Add context about voice input
        voice_prompt = f"[Voice message transcription]: {transcribed_text}\n\nRespond as Sifu to this Cantonese audio."

        # Process as text
        return await self.process_text(voice_prompt, conversation_history, user_facts)
