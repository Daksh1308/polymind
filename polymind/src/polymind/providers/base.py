import json
import os
import time
from abc import ABC, abstractmethod
from typing import AsyncIterator

import httpx

from polymind.models import ProviderResponse

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class Provider(ABC):
    name: str = ""

    def __init__(self, config):
        self._config = config

    @property
    def method(self) -> str:
        return "api"

    @property
    def configured(self) -> bool:
        return "OPENROUTER_API_KEY" in os.environ

    @abstractmethod
    async def query(self, question: str) -> AsyncIterator[str]:
        ...

    async def run(self, question: str) -> ProviderResponse:
        start = time.monotonic()
        tokens: list[str] = []
        try:
            async for token in self.query(question):
                tokens.append(token)
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            return ProviderResponse(
                provider=self.name,
                method=self.method,
                model=self._model_name(),
                content="",
                error=str(e),
                duration_ms=duration,
            )
        duration = int((time.monotonic() - start) * 1000)
        return ProviderResponse(
            provider=self.name,
            method=self.method,
            model=self._model_name(),
            content="".join(tokens),
            error=None,
            duration_ms=duration,
        )

    def _model_name(self) -> str:
        return "unknown"


class OpenRouterProvider(Provider):
    model: str = ""

    async def query(self, question: str) -> AsyncIterator[str]:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            yield "[Error: OPENROUTER_API_KEY not set]"
            return

        effective_model = resolve_model_override(self.name, self.model)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/anthropics/claude-code",
            "X-Title": "Polymind",
        }
        body = {
            "model": effective_model,
            "messages": [{"role": "user", "content": question}],
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", OPENROUTER_URL, json=body, headers=headers
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        choices = chunk.get("choices")
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        token: str | None = delta.get("content")
                        if token:
                            yield token

    def _model_name(self) -> str:
        return resolve_model_override(self.name, self.model)


def resolve_model_override(name: str, default: str) -> str:
    env_key = f"POLYMIND_MODEL_{name.upper()}"
    return os.environ.get(env_key, default)
