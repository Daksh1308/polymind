---
description: Show which AI providers (OpenAI, Gemini, Grok, Perplexity) are configured and available for polymind queries.
disable-model-invocation: true
allowed-tools: Bash
---

## Polymind Status

The user wants to see which AI providers are connected and ready to use.

1. Run `polymind status --json` to check all provider configurations.
2. If `polymind` is not installed, tell the user:
   > Polymind is not installed. Run: `pip install -e ~/dev/polymind`
3. Display the results as a formatted table with these columns: Provider, Status, Method, Detail.

Use a checkmark (✅) for available providers and a cross (❌) for unavailable ones.

If a provider shows status "available" but method "api", the user has an API key set. If method is "cli", they have a CLI tool installed.

Example output:
| Provider | Status | Method | Detail |
|---|---|---|---|
| openai | ✅ | api | API key: sk-proj-... |
| gemini | ❌ | — | not configured |
