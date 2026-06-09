from polymind.providers.base import OpenRouterProvider


class OpenAIProvider(OpenRouterProvider):
    name = "openai"
    model = "openrouter/free"
