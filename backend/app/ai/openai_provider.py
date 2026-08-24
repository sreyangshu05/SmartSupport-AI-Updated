"""OpenAI-compatible provider.

Talks to any OpenAI-compatible chat/completions + embeddings endpoint. Works
with the official OpenAI API, Azure endpoints, or self-hosted proxies (vLLM,
Ollama with an OpenAI shim, LM Studio, etc.) by setting ``AI_BASE_URL``.
"""
from __future__ import annotations

import hashlib
import time

import httpx
from tenacity import RetryError, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.ai.base import AINotConfigured, AIProviderError, BaseAIProvider, GenerationResult
from app.core.config import get_settings

settings = get_settings()


class OpenAICompatProvider(BaseAIProvider):
    name = "openai_compat"

    def __init__(self) -> None:
        self.base_url = settings.AI_BASE_URL.rstrip("/")
        self.api_key = settings.AI_API_KEY
        self.chat_model = settings.AI_CHAT_MODEL
        self.embedding_model = settings.AI_EMBEDDING_MODEL
        self.timeout = settings.AI_REQUEST_TIMEOUT_SECONDS

    def is_configured(self) -> bool:
        # Embeddings-only usage without a chat key is unusual; require the key.
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _raise_if_unconfigured(self) -> None:
        if not self.is_configured():
            raise AINotConfigured(
                "AI_PROVIDER is openai_compat but AI_API_KEY is not set"
            )

    @staticmethod
    def _response_excerpt(response: httpx.Response) -> str:
        text = response.text.strip().replace("\n", " ")
        return text[:300] if text else "no response body"

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(settings.AI_MAX_RETRIES),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> GenerationResult:
        self._raise_if_unconfigured()
        payload = {
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        start = time.monotonic()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                raise AINotConfigured(
                    "AI provider rejected credentials "
                    f"(HTTP {exc.response.status_code}): "
                    f"{self._response_excerpt(exc.response)}"
                ) from exc
            if exc.response.status_code == 429:
                raise AIProviderError("AI provider rate limit exceeded") from exc
            raise AIProviderError(
                f"AI provider returned HTTP {exc.response.status_code}: "
                f"{self._response_excerpt(exc.response)}"
            ) from exc
        except RetryError as exc:
            raise AIProviderError("AI provider unreachable after retries") from exc

        latency = int((time.monotonic() - start) * 1000)
        try:
            choice = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
        except (KeyError, IndexError) as exc:
            raise AIProviderError("Malformed AI provider response") from exc

        return GenerationResult(
            text=choice or "",
            model=self.chat_model,
            usage={**usage, "latency_ms": latency},
        )

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(1),
        reraise=True,
    )
    def embed(self, texts: list[str]) -> list[list[float]]:
        self._raise_if_unconfigured()
        payload = {"model": self.embedding_model, "input": texts}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/embeddings",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                raise AINotConfigured(
                    "AI provider rejected credentials "
                    f"(HTTP {exc.response.status_code}): "
                    f"{self._response_excerpt(exc.response)}"
                ) from exc
            raise AIProviderError(
                f"AI provider returned HTTP {exc.response.status_code}: "
                f"{self._response_excerpt(exc.response)}"
            ) from exc

        try:
            return [item["embedding"] for item in data["data"]]
        except (KeyError, IndexError) as exc:
            raise AIProviderError("Malformed embeddings response") from exc

    @staticmethod
    def hash_input(*parts: str) -> str:
        joined = "|".join(parts or [""])
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def get_provider() -> BaseAIProvider:
    return OpenAICompatProvider()
