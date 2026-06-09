from polymind.providers.base import Provider
from polymind.providers.openai import OpenAIProvider
from polymind.providers.gemini import GeminiProvider
from polymind.providers.grok import GrokProvider
from polymind.providers.perplexity import PerplexityProvider

PROVIDER_MAP: dict[str, type[Provider]] = {
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "grok": GrokProvider,
    "perplexity": PerplexityProvider,
}


def get_provider(name: str, config) -> Provider | None:
    cls = PROVIDER_MAP.get(name)
    if cls is None:
        return None
    return cls(config)
