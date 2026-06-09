from polymind.providers.base import OpenRouterProvider


class PerplexityProvider(OpenRouterProvider):
    name = "perplexity"
    model = "openrouter/free"
