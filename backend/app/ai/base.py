"""AI provider interface.

All production AI flows go through an implementation of ``BaseAIProvider``.
Providers are selected by environment configuration (``AI_PROVIDER``). The
application never hardcodes a single vendor, and never presents deterministic
keyword heuristics as production AI.

A provider raises ``AINotConfigured`` when credentials are missing so callers
can surface a clear "AI not configured" state instead of silently degrading.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class AINotConfigured(Exception):
    """Raised when the configured AI provider has no usable credentials."""


class AIProviderError(Exception):
    """Raised when the AI provider call fails for a non-config reason."""


@dataclass
class GenerationResult:
    text: str
    model: str | None = None
    usage: dict = field(default_factory=dict)


class BaseAIProvider:
    """Interface contract for AI providers.

    Subclasses implement the chat + embedding methods. Raise :class:`AINotConfigured`
    in ``__init__`` or on first use when setup is incomplete.
    """

    name: str = "base"

    def is_configured(self) -> bool:
        raise NotImplementedError

    def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> GenerationResult:
        raise NotImplementedError

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError
