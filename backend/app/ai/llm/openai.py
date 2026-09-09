from app.ai.llm.base import LLMProvider
from app.ai.llm.failover import FailoverLLMProvider
from app.ai.llm.gemini import GeminiLLMProvider
from app.ai.llm.nvidia_nim import NvidiaNIMProvider
from app.ai.llm.openai_provider import OpenAIProvider

# Backward compatibility alias
OpenAILLMProvider = GeminiLLMProvider


def get_llm_provider() -> LLMProvider:
    return FailoverLLMProvider()
