import logging
from typing import TypeVar
from pydantic import BaseModel

from app.ai.llm.base import LLMProvider
from app.ai.llm.gemini import GeminiLLMProvider
from app.ai.llm.nvidia_nim import NvidiaNIMProvider
from app.ai.llm.openai_provider import OpenAIProvider
from app.core.config import settings
from app.core.exceptions import AIServiceError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class FailoverLLMProvider(LLMProvider):
    """Orchestrates an ordered chain of LLM providers (Gemini, OpenAI, NVIDIA NIM).
    If a model or provider fails, is rate limited, or experiences high demand (e.g. 503),
    execution seamlessly fails over to the next available provider in the chain."""

    def __init__(self, providers: list[LLMProvider] | None = None) -> None:
        if providers is not None:
            self.providers = providers
        else:
            self.providers = self._build_default_providers()

    def _build_default_providers(self) -> list[LLMProvider]:
        provider_map = {
            "gemini": GeminiLLMProvider,
            "openai": OpenAIProvider,
            "nvidia": NvidiaNIMProvider,
            "nvidia_nim": NvidiaNIMProvider,
        }

        priority_order = [p.strip().lower() for p in settings.llm_provider_priority.split(",") if p.strip()]
        instantiated: list[LLMProvider] = []

        for name in priority_order:
            cls = provider_map.get(name)
            if not cls:
                continue
            try:
                prov = cls()
                if prov.is_available():
                    instantiated.append(prov)
            except Exception as exc:
                logger.warning("Could not initialize provider %s: %s", name, exc)

        # Fallback: if none of the priority matches, check any provider with a key
        if not instantiated:
            for name, cls in provider_map.items():
                if name in ("nvidia_nim",):
                    continue
                try:
                    prov = cls()
                    if prov.is_available():
                        instantiated.append(prov)
                except Exception:
                    pass

        return instantiated

    @property
    def available_providers(self) -> list[LLMProvider]:
        return [p for p in self.providers if getattr(p, "is_available", lambda: True)()]

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        active = self.available_providers
        if not active:
            raise AIServiceError(
                "No AI provider is configured. Please configure at least one of "
                "GEMINI_API_KEY, OPENAI_API_KEY, or NVIDIA_API_KEY."
            )

        last_error: Exception | None = None
        for i, provider in enumerate(active):
            name = getattr(provider, "provider_name", provider.__class__.__name__)
            logger.info("Executing completion with provider: %s (%d/%d)", name, i + 1, len(active))
            try:
                return await provider.complete(system_prompt=system_prompt, user_prompt=user_prompt)
            except Exception as exc:
                last_error = exc
                next_provider = active[i + 1] if i + 1 < len(active) else None
                next_name = getattr(next_provider, "provider_name", "None") if next_provider else "none"
                logger.warning(
                    "Provider '%s' failed (%s). Failing over to next provider '%s'...",
                    name,
                    exc,
                    next_name,
                )

        raise AIServiceError(f"All configured AI providers failed: {last_error}") from last_error

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        max_retries: int = 2,
    ) -> T:
        active = self.available_providers
        if not active:
            raise AIServiceError(
                "No AI provider is configured. Please configure at least one of "
                "GEMINI_API_KEY, OPENAI_API_KEY, or NVIDIA_API_KEY."
            )

        last_error: Exception | None = None
        for i, provider in enumerate(active):
            name = getattr(provider, "provider_name", provider.__class__.__name__)
            logger.info("Executing generate_structured with provider: %s (%d/%d)", name, i + 1, len(active))
            try:
                return await provider.generate_structured(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_model=response_model,
                    max_retries=max_retries,
                )
            except Exception as exc:
                last_error = exc
                next_provider = active[i + 1] if i + 1 < len(active) else None
                next_name = getattr(next_provider, "provider_name", "None") if next_provider else "none"
                logger.warning(
                    "Provider '%s' failed during structured generation (%s). Failing over to '%s'...",
                    name,
                    exc,
                    next_name,
                )

        raise AIServiceError(
            f"All AI providers failed to generate valid {response_model.__name__}: {last_error}"
        ) from last_error
