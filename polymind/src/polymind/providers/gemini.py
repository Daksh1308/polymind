from polymind.providers.base import OpenRouterProvider


class GeminiProvider(OpenRouterProvider):
    name = "gemini"
    model = "openrouter/free"
