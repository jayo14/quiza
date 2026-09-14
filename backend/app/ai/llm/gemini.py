import asyncio
import logging
import re
import time
from google import genai
from google.genai import types

from app.ai.llm.base import LLMProvider
from app.core.config import settings
from app.core.exceptions import AIServiceError

logger = logging.getLogger(__name__)


def parse_retry_delay(exc: Exception) -> float | None:
    """Extract retryDelay from Gemini API error responses (e.g. '30s', '60s')."""
    msg = str(exc)
    match = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+)s", msg)
    if match:
        return float(match.group(1))
    return None


class GeminiLLMProvider(LLMProvider):
    def __init__(self, model: str | None = None, fallback_models: list[str] | None = None) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self.primary_model = model or settings.gemini_chat_model

        if fallback_models is not None:
            self.fallback_models = fallback_models
        else:
            configured = [m.strip() for m in settings.gemini_fallback_models.split(",") if m.strip()]
            self.fallback_models = [m for m in configured if m != self.primary_model]

        # All candidate models in order: primary first, then fallbacks
        self.models = [self.primary_model] + [m for m in self.fallback_models if m != self.primary_model]
        self._cooldowns: dict[str, float] = {}

    @property
    def provider_name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        return bool(settings.gemini_api_key)

    def _is_cooling_down(self, model: str) -> bool:
        expires = self._cooldowns.get(model, 0.0)
        return time.time() < expires

    def _set_cooldown(self, model: str, duration: float | None = None) -> None:
        cooldown = duration or float(settings.llm_model_cooldown_seconds)
        self._cooldowns[model] = time.time() + cooldown
        logger.warning(
            "Gemini model '%s' placed in cooldown for %ds due to overload/exhaustion.",
            model,
            int(cooldown),
        )

    def _is_permanent_model_error(self, exc: Exception) -> bool:
        msg = str(exc).lower()
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        return (
            status in (404, 410)
            or "404" in msg
            or "410" in msg
            or "not found" in msg
            or "end of life" in msg
            or "no longer available" in msg
            or "does not exist" in msg
            or "model_not_found" in msg
        )

    def _is_transient_or_demand_error(self, exc: Exception) -> bool:
        msg = str(exc).lower()
        transient_indicators = [
            "503",
            "unavailable",
            "high demand",
            "temporarily overloaded",
            "spikes in demand",
            "resource_exhausted",
            "429",
            "rate limit",
            "quota",
            "server error",
            "timeout",
        ]
        return any(indicator in msg for indicator in transient_indicators)

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        if not self.is_available():
            raise AIServiceError("Gemini API key is not configured.")

        # Try active models in order, skipping cooled-down ones if alternatives exist
        candidate_models = [m for m in self.models if not self._is_cooling_down(m)]
        if not candidate_models:
            sorted_models = sorted(self.models, key=lambda m: self._cooldowns.get(m, 0.0))
            earliest_expiry = self._cooldowns.get(sorted_models[0], 0.0)
            wait_time = max(0.0, earliest_expiry - time.time())
            if wait_time < 120:
                logger.info("All Gemini models in cooldown. Waiting %.1fs for earliest expiry...", wait_time)
                await asyncio.sleep(wait_time)
                candidate_models = [m for m in self.models if not self._is_cooling_down(m)]
            if not candidate_models:
                candidate_models = sorted_models

        last_error: Exception | None = None

        for model in candidate_models:
            logger.info("Attempting completion with Gemini model: %s", model)
            try:
                response = await self._client.aio.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        temperature=0.3,
                    ),
                )
                if not response.text:
                    raise AIServiceError(f"Gemini model {model} returned an empty response.")
                return response.text
            except Exception as exc:
                last_error = exc
                if self._is_permanent_model_error(exc):
                    self._set_cooldown(model, 86400.0)
                    logger.warning(
                        "Gemini model %s returned 404/410 (model deprecated or not found). Cooldown 24h. Falling over...",
                        model,
                    )
                elif self._is_transient_or_demand_error(exc):
                    retry_delay = parse_retry_delay(exc)
                    self._set_cooldown(model, retry_delay)
                    logger.warning(
                        "Gemini model %s failed with transient/demand error (%s). Cooldown %ds. Falling over...",
                        model,
                        exc,
                        int(retry_delay or settings.llm_model_cooldown_seconds),
                    )
                else:
                    logger.warning(
                        "Gemini model %s failed with error (%s). Trying next fallback model...",
                        model,
                        exc,
                    )

        raise AIServiceError(f"All Gemini models failed: {last_error}") from last_error
