import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class GenerationContextManager:
    """Manages mid-task continuation context across LLM calls and failover providers.
    Tracks accumulated items (e.g. quiz questions), formats non-redundant continuation
    prompts, and ensures subsequent models seamlessly resume where previous models stopped."""

    def __init__(self, target_count: int) -> None:
        self.target_count = target_count
        self.accumulated: list[Any] = []
        self._seen_signatures: set[str] = set()

    @property
    def remaining_count(self) -> int:
        return max(0, self.target_count - len(self.accumulated))

    @property
    def is_complete(self) -> bool:
        return len(self.accumulated) >= self.target_count

    def normalize(self, text: str) -> str:
        return " ".join(text.lower().split())

    def add_unique(self, items: list[Any], key_fn: Callable[[Any], str]) -> list[Any]:
        added: list[Any] = []
        for item in items:
            if len(self.accumulated) >= self.target_count:
                break
            sig = self.normalize(key_fn(item))
            if sig not in self._seen_signatures:
                self._seen_signatures.add(sig)
                self.accumulated.append(item)
                added.append(item)
        return added

    def build_continuation_prompt(self, summary_fn: Callable[[Any], str]) -> str:
        """Constructs context instructions informing the model of already generated
        items so the failover model never creates redundant questions or repeats facts."""
        if not self.accumulated:
            return ""

        summary_lines = [f"- {summary_fn(item)}" for item in self.accumulated]
        summary_text = "\n".join(summary_lines)

        return (
            f"\n\n--- MID-TASK CONTINUATION CONTEXT ---\n"
            f"Note: {len(self.accumulated)} item(s) have ALREADY been successfully produced for this task:\n"
            f"{summary_text}\n\n"
            f"CRITICAL REQUIREMENT: Do NOT duplicate, repeat, or closely rephrase any of the above items. "
            f"Continue from where the previous model stopped and generate ONLY the remaining {self.remaining_count} "
            f"unique item(s) strictly matching all required specifications."
        )
