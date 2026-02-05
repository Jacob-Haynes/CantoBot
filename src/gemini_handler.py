"""Google Gemini API handler for AI conversation processing."""

from google import genai
from google.genai import types
import logging
import asyncio
import time
from typing import Any

from .prompts import SYSTEM_PROMPT_TEMPLATE
from .tools import AVAILABLE_TOOLS

logger = logging.getLogger(__name__)


class GeminiHandler:
    """Handler for Google Gemini API interactions."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp") -> None:
        # Initialize client with new API
        self.client = genai.Client(api_key=api_key)

        # Configure safety settings (block only high-probability harmful content)
        self.safety_settings = [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH
            )
        ]

        # Store model name
        self.model_name = model_name

        # Configure generation settings with tools
        self.generation_config = types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=2048,
            safety_settings=self.safety_settings,
            tools=AVAILABLE_TOOLS  # Tools go inside config, not as separate parameter
        )

        logger.info(f"Gemini handler initialized with model: {model_name}")
        logger.info(f"Tools enabled: {[tool.__name__ for tool in AVAILABLE_TOOLS]}")

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

    async def _execute_function_call(self, function_call: Any) -> dict[str, Any]:
        """
        Execute a function call requested by the model.

        Args:
            function_call: Function call object from Gemini response

        Returns:
            Function response dict with name and result
        """
        func_name: str = function_call.name
        func_args: dict[str, Any] = dict(function_call.args)

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

    async def process_text(self, text: str, conversation_history: list[dict[str, str]], user_facts: dict[str, str]) -> str:
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

        # Build conversation history for new API
        contents = [types.Content(role="user", parts=[types.Part(text=system_prompt)])]

        # Add conversation history
        for msg in conversation_history:
            contents.append(
                types.Content(
                    role=msg["role"],
                    parts=[types.Part(text=msg["content"])]
                )
            )

        # Add current message
        contents.append(types.Content(role="user", parts=[types.Part(text=text)]))

        # Generate response with retry logic
        for attempt in range(3):
            try:
                logger.info(f"Sending text request to Gemini (attempt {attempt + 1})")

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=contents,
                    config=self.generation_config
                )

                # Handle function calls if present
                if response.candidates and response.candidates[0].content.parts:
                    # Check for function calls
                    function_calls = [
                        part.function_call
                        for part in response.candidates[0].content.parts
                        if hasattr(part, 'function_call') and part.function_call
                    ]

                    if function_calls:
                        logger.info(f"Model requested {len(function_calls)} function call(s)")

                        # Execute all function calls
                        function_response_parts = []
                        for fc in function_calls:
                            func_result = await self._execute_function_call(fc)
                            function_response_parts.append(
                                types.Part(
                                    function_response=types.FunctionResponse(
                                        name=func_result["name"],
                                        response={"result": func_result["result"]}
                                    )
                                )
                            )

                        # Add function call request and responses to history
                        contents.append(response.candidates[0].content)
                        contents.append(types.Content(role="function", parts=function_response_parts))

                        # Send function results back to continue conversation
                        logger.info("Sending function results back to model")
                        response = await asyncio.to_thread(
                            self.client.models.generate_content,
                            model=self.model_name,
                            contents=contents,
                            config=self.generation_config
                        )

                result: str = response.text
                logger.info(f"Received response: {result[:100]}...")
                return result

            except Exception as e:
                logger.error(f"Error processing text (attempt {attempt + 1}): {e}")
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        raise RuntimeError("Failed to process text after 3 attempts")

    async def process_audio(self, audio_path: str, conversation_history: list[dict[str, str]], user_facts: dict[str, str]) -> str:
        """
        Process an audio file and generate a response.

        Args:
            audio_path: Path to audio file
            conversation_history: Recent conversation history
            user_facts: User facts from database

        Returns:
            AI-generated response text
        """
        system_prompt: str = self.build_system_prompt(user_facts)

        # Upload audio file using new API
        logger.info(f"Uploading audio file: {audio_path}")
        audio_file = await asyncio.to_thread(
            self.client.files.upload,
            path=audio_path
        )

        # Wait for file processing if needed
        max_wait: int = 30  # seconds
        start_time: float = time.time()
        while audio_file.state == "PROCESSING":
            if time.time() - start_time > max_wait:
                raise TimeoutError("Audio file processing timeout")

            logger.debug("Waiting for audio file processing...")
            await asyncio.sleep(1)
            audio_file = await asyncio.to_thread(
                self.client.files.get,
                name=audio_file.name
            )

        if audio_file.state == "FAILED":
            raise RuntimeError("Audio file processing failed")

        logger.info(f"Audio file ready: {audio_file.name}")

        try:
            # Build conversation history with system prompt
            contents = [types.Content(role="user", parts=[types.Part(text=system_prompt)])]

            # Add conversation history
            for msg in conversation_history:
                contents.append(
                    types.Content(
                        role=msg["role"],
                        parts=[types.Part(text=msg["content"])]
                    )
                )

            # Add audio file and prompt
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part(file_data=types.FileData(file_uri=audio_file.uri)),
                        types.Part(text="Listen to this Cantonese audio and respond as Sifu.")
                    ]
                )
            )

            # Generate response with retry logic
            for attempt in range(3):
                try:
                    logger.info(f"Sending audio request to Gemini (attempt {attempt + 1})")
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.model_name,
                        contents=contents,
                        config=self.generation_config
                    )

                    # Handle function calls if present
                    if response.candidates and response.candidates[0].content.parts:
                        # Check for function calls
                        function_calls = [
                            part.function_call
                            for part in response.candidates[0].content.parts
                            if hasattr(part, 'function_call') and part.function_call
                        ]

                        if function_calls:
                            logger.info(f"Model requested {len(function_calls)} function call(s)")

                            # Execute all function calls
                            function_response_parts = []
                            for fc in function_calls:
                                func_result = await self._execute_function_call(fc)
                                function_response_parts.append(
                                    types.Part(
                                        function_response=types.FunctionResponse(
                                            name=func_result["name"],
                                            response={"result": func_result["result"]}
                                        )
                                    )
                                )

                            # Add function call request and responses to history
                            contents.append(response.candidates[0].content)
                            contents.append(types.Content(role="function", parts=function_response_parts))

                            # Send function results back to continue conversation
                            logger.info("Sending function results back to model")
                            response = await asyncio.to_thread(
                                self.client.models.generate_content,
                                model=self.model_name,
                                contents=contents,
                                config=self.generation_config
                            )

                    result: str = response.text
                    logger.info(f"Received response: {result[:100]}...")
                    return result

                except Exception as e:
                    logger.error(f"Error processing audio (attempt {attempt + 1}): {e}")
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

            raise RuntimeError("Failed to process audio after 3 attempts")

        finally:
            # Cleanup uploaded file
            try:
                await asyncio.to_thread(self.client.files.delete, name=audio_file.name)
                logger.debug(f"Deleted uploaded file: {audio_file.name}")
            except Exception as e:
                logger.warning(f"Failed to delete uploaded file: {e}")
