from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.ai.llm.base import LLMProvider
from app.core.config import settings
from app.core.exceptions import AIServiceError


class GeminiLLMProvider(LLMProvider):
    def __init__(self, model: str | None = None) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = model or settings.gemini_chat_model

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )
        except APIError as exc:
            raise AIServiceError(f"The AI provider returned an error: {exc}") from exc
        except Exception as exc:
            raise AIServiceError(f"The AI provider request failed: {exc}") from exc

        if not response.text:
            raise AIServiceError("The AI provider returned an empty response.")
        return response.text


# Backward compatibility alias
OpenAILLMProvider = GeminiLLMProvider


def get_llm_provider() -> LLMProvider:
    return GeminiLLMProvider()
