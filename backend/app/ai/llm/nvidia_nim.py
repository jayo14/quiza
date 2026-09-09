import logging
import time
from openai import AsyncOpenAI

from app.ai.llm.base import LLMProvider
from app.core.config import settings
from app.core.exceptions import AIServiceError

logger = logging.getLogger(__name__)


class NvidiaNIMProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        fallback_models: list[str] | None = None,
    ) -> None:
        self._api_key = api_key or settings.nvidia_api_key
        self._base_url = base_url or settings.nvidia_base_url
        self.primary_model = model or settings.nvidia_chat_model

        if fallback_models is not None:
            self.fallback_models = fallback_models
        else:
            configured = [m.strip() for m in settings.nvidia_fallback_models.split(",") if m.strip()]
            self.fallback_models = [m for m in configured if m != self.primary_model]

        self.models = [self.primary_model] + [m for m in self.fallback_models if m != self.primary_model]
        self._cooldowns: dict[str, float] = {}

        if self.is_available():
            self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        else:
            self._client = None

    @property
    def provider_name(self) -> str:
        return "nvidia_nim"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _is_cooling_down(self, model: str) -> bool:
        expires = self._cooldowns.get(model, 0.0)
        return time.time() < expires

    def _set_cooldown(self, model: str, duration: float = 60.0) -> None:
        self._cooldowns[model] = time.time() + duration
        logger.warning(
            "NVIDIA NIM model '%s' placed in cooldown for %ds due to overload/exhaustion.",
            model,
            int(duration),
        )

    def _is_transient_or_demand_error(self, exc: Exception) -> bool:
        msg = str(exc).lower()
        transient_indicators = [
            "503",
            "unavailable",
            "429",
            "rate_limit",
            "rate limit",
            "quota",
            "server_error",
            "timeout",
        ]
        return any(indicator in msg for indicator in transient_indicators)

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        if not self.is_available() or self._client is None:
            raise AIServiceError("NVIDIA NIM API key is not configured.")

        candidate_models = [m for m in self.models if not self._is_cooling_down(m)]
        if not candidate_models:
            candidate_models = sorted(self.models, key=lambda m: self._cooldowns.get(m, 0.0))

        last_error: Exception | None = None

        for model in candidate_models:
            logger.info("Attempting completion with NVIDIA NIM model: %s", model)
            try:
                # Some NIM models support response_format json_object, try with it or fallback gracefully
                try:
                    response = await self._client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.3,
                    )
                except Exception as format_exc:
                    if "response_format" in str(format_exc).lower():
                        response = await self._client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=0.3,
                        )
                    else:
                        raise format_exc

                choice = response.choices[0]
                content = choice.message.content
                if not content:
                    raise AIServiceError(f"NVIDIA NIM model {model} returned an empty response.")
                return content
            except Exception as exc:
                last_error = exc
                if self._is_transient_or_demand_error(exc):
                    self._set_cooldown(model, float(settings.llm_model_cooldown_seconds))
                    logger.warning(
                        "NVIDIA NIM model %s failed with transient error (%s). Falling over to next model...",
                        model,
                        exc,
                    )
                else:
                    logger.warning(
                        "NVIDIA NIM model %s failed with error (%s). Trying next fallback model...",
                        model,
                        exc,
                    )

        raise AIServiceError(f"All NVIDIA NIM models failed: {last_error}") from last_error
