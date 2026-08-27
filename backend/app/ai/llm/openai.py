from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.ai.llm.base import LLMProvider
from app.core.config import settings
from app.core.exceptions import AIServiceError


class OpenAILLMProvider(LLMProvider):
    def __init__(self, model: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = model or settings.openai_chat_model

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
        except RateLimitError as exc:
            raise AIServiceError("The AI provider is rate-limiting requests, try again shortly.") from exc
        except APITimeoutError as exc:
            raise AIServiceError("The AI provider timed out.") from exc
        except APIError as exc:
            raise AIServiceError(f"The AI provider returned an error: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise AIServiceError("The AI provider returned an empty response.")
        return content


def get_llm_provider() -> LLMProvider:
    return OpenAILLMProvider()
