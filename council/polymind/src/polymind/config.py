import os
from typing import NamedTuple


class ProviderConfig(NamedTuple):
    name: str
    default_model: str

    @property
    def available(self) -> bool:
        return "OPENROUTER_API_KEY" in os.environ

    @property
    def method(self) -> str:
        return "api" if self.available else "unavailable"


PROVIDER_CONFIGS: list[ProviderConfig] = [
    ProviderConfig("openai", "openrouter/free"),
    ProviderConfig("gemini", "openrouter/free"),
    ProviderConfig("grok", "openrouter/free"),
    ProviderConfig("perplexity", "openrouter/free"),
]

_MODEL_OVERRIDES = {
    "openai": "POLYMIND_MODEL_OPENAI",
    "gemini": "POLYMIND_MODEL_GEMINI",
    "grok": "POLYMIND_MODEL_GROK",
    "perplexity": "POLYMIND_MODEL_PERPLEXITY",
}


def resolve_model(name: str, default: str) -> str:
    env_key = _MODEL_OVERRIDES.get(name)
    if env_key and env_key in os.environ:
        return os.environ[env_key]
    return default


def get_provider_config(name: str) -> ProviderConfig | None:
    for pc in PROVIDER_CONFIGS:
        if pc.name == name:
            return pc
    return None


def get_available_providers(names: list[str] | None = None) -> list[ProviderConfig]:
    if names:
        selected = [get_provider_config(n) for n in names]
        return [pc for pc in selected if pc and pc.available]
    return [pc for pc in PROVIDER_CONFIGS if pc.available]


def status_report() -> list[dict]:
    available = "OPENROUTER_API_KEY" in os.environ
    rows = []
    for pc in PROVIDER_CONFIGS:
        model = resolve_model(pc.name, pc.default_model)
        detail = f"via OpenRouter ({model})" if available else "not configured"
        if available:
            key = os.environ.get("OPENROUTER_API_KEY", "")
            masked = key[:12] + "..." if len(key) > 16 else "set"
            detail += f" — key: {masked}"
        rows.append({
            "provider": pc.name,
            "available": available,
            "method": "api" if available else "—",
            "model": model if available else "—",
            "detail": detail,
        })
    return rows
