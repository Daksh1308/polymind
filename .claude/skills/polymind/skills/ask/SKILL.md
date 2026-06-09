---
description: Ask one question to multiple AI coding assistants (OpenAI, Gemini, Grok, Perplexity) and see their answers side by side with an agreement/disagreement/safest-choice summary.
disable-model-invocation: true
allowed-tools: Bash Read Write
---

# Polymind Ask

The user wants to ask a question to multiple AI providers and see their answers compared.

## 1. Check Setup

```!
polymind status --json 2>/dev/null || echo "NOT_INSTALLED"
```

If `polymind` is not available, tell the user to run:
```
pip install -e $PWD/polymind
```
and stop. Then make sure `OPENROUTER_API_KEY` is set in their environment.

## 2. Parse Arguments

The user typed: `$ARGUMENTS`

Extract these optional flags from the argument string:
- `--providers <comma-separated>` — specific providers (e.g. `--providers openai,grok`)
- `--file <path>` — include a file for review (read it with the Read tool)
- `--roles <comma-separated>` — review roles: security, performance, simplicity, maintainability
- `--save` — save the response to a markdown file
- `--summary-only` — show only the summary, skip full responses
- `--debate` — run a multi-round debate between providers

Everything else is the **question**. If no question is found, ask the user what they want to ask.

## 3. Gather Context (if --file)

If `--file <path>` is present, use the Read tool to read the file's contents. Store the file path to pass to polymind.

## 4. Run Polymind

Build and execute a command like:

```
polymind ask \
  "the question here" \
  --providers openai,gemini,grok,perplexity \
  --format json
```

Only add flags that the user provided:
- Include `--providers` only if the user specified it (otherwise polymind auto-detects)
- Include `--file <path>` only if provided
- Include `--roles <roles>` only if provided
- Include `--debate` only if provided
- Do NOT include `--save` or `--summary-only` in the polymind command (those are handled below)

## 5. Process the JSON Output

The JSON output will contain:
```json
{
  "meta": { "question": "...", "timestamp": "..." },
  "responses": [
    {
      "provider": "openai",
      "method": "api",
      "model": "gpt-4o",
      "content": "...full response text...",
      "error": null,
      "duration_ms": 2345
    }
  ]
}
```

## 6. Display Results

Unless `--summary-only` was given, display each provider's response in a clearly labeled section:

**Provider:** OpenAI (gpt-4o via API · 2345ms)
```
[...response content...]
```

Use a horizontal rule between providers. Add an error indicator if a provider failed.

If `--debate` was used, also show the second round critique responses under each provider label.

## 7. Generate Comparison Analysis

At the bottom, add a **Summary** section with:

### Where They Agree
Read all responses and identify 2-5 specific points that most providers converged on.

### Where They Disagree
Read all responses and identify 1-3 specific differences in their recommendations or approaches.

### Safest Choice
Based on the agreement and disagreement points, recommend the most conservative, risk-aware choice. Explain your reasoning in 2-3 sentences. Consider:
- Which approach is most widely recommended
- Which approach has the fewest downsides
- Which is safest for production use

If `--roles` was specified (security, performance, simplicity, maintainability), add a **Role-Based Scoring** section that evaluates each provider's response against each role criterion.

## 8. Handle --save

If `--save` was given, write a formatted markdown file named `polymind-<date>.md` with:
- The question
- Each provider's full response
- The comparison analysis
- Metadata (timestamp, models used)

Tell the user the file was saved.

## 9. Handle --summary-only

If `--summary-only` was given, skip step 6 (do not show individual responses) and only show the Summary section (step 7). Note "summary only mode" at the top.

## Usage Examples

```
/polymind:ask What is Rust?
/polymind:ask --providers openai,grok What is the best way to handle errors?
/polymind:ask --file src/main.py --roles security,performance Review this
/polymind:ask --save --summary-only What database should I use?
/polymind:ask --debate Should I use PostgreSQL or SQLite?
```
