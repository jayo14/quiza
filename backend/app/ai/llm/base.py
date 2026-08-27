import json
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.exceptions import AIServiceError

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Abstraction over a chat-completion LLM. Concrete providers (OpenAI, etc.)
    implement `complete`; the rest of the app depends only on this interface so the
    provider can be swapped without touching callers."""

    @abstractmethod
    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        """Return the raw text completion for a single-turn prompt."""
        raise NotImplementedError

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        max_retries: int = 2,
    ) -> T:
        """Call the LLM and parse its output into `response_model`, retrying with
        the validation error fed back to the model if the first attempt is malformed
        JSON or fails schema validation. Raises AIServiceError if every attempt fails,
        so a flaky or misbehaving model never crashes the request."""

        schema_hint = json.dumps(response_model.model_json_schema(), indent=2)
        full_system_prompt = (
            f"{system_prompt}\n\n"
            "Respond with ONLY a single JSON object (no markdown fences, no prose) "
            f"that matches this JSON schema:\n{schema_hint}"
        )

        last_error: Exception | None = None
        current_user_prompt = user_prompt

        for attempt in range(max_retries + 1):
            try:
                raw = await self.complete(
                    system_prompt=full_system_prompt, user_prompt=current_user_prompt
                )
                cleaned = _strip_code_fences(raw)
                data = json.loads(cleaned)
                return response_model.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                current_user_prompt = (
                    f"{user_prompt}\n\n"
                    f"Your previous response was invalid: {exc}\n"
                    "Return corrected JSON that strictly matches the schema."
                )
            except Exception as exc:  # upstream API failure, timeout, rate limit, etc.
                last_error = exc
                break

        raise AIServiceError(
            f"LLM failed to produce a valid {response_model.__name__} after "
            f"{max_retries + 1} attempt(s): {last_error}"
        )


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped
