from polymind.providers.base import OpenRouterProvider


class GrokProvider(OpenRouterProvider):
    name = "grok"
    model = "openrouter/free"
