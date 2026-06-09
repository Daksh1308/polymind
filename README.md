# Polymind

**Query multiple AI coding assistants at once, compare their answers side by side, and get an agreement/safest-choice summary.**

Polymind lets you ask one question and get responses from OpenAI (GPT-4o), Google Gemini, xAI Grok, and Perplexity in parallel. Use it standalone from your terminal, as a `/polymind:ask` slash command inside Claude Code, or through the browser-based web UI.

---

## Features

- **Multi-provider queries** — Ask one question, get answers from all configured AI providers
- **Parallel streaming** — Responses arrive in real time as tokens stream in
- **Side-by-side display** — Each provider's answer in a labeled panel (rich terminal) or formatted sections (Claude Code)
- **Agreement analysis** — Finds where providers converge and where they differ
- **Safest choice recommendation** — Suggests the most conservative, production-safe option
- **Code review roles** — Evaluate responses against security, performance, simplicity, and maintainability criteria
- **File review** — Include a source file for multi-AI code review (`--file`)
- **Debate mode** — Two rounds: initial answers → cross-critique → final synthesis (`--debate`)
- **Markdown export** — Save results to a markdown report (`--save`)
- **tmux side pane** — Stream responses into a tmux split pane when inside tmux (`--tmux`)
- **Claude Code integration** — Use as `/polymind:ask` and `/polymind:status` commands
- **Web UI** — Browser-based chat interface with live SSE streaming, toggleable providers, code attachment, and role selection

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Async HTTP | [httpx](https://www.python-httpx.org/) (parallel streaming) |
| Terminal UI | [rich](https://github.com/Textualize/rich) (live panels, tables) |
| Web framework | [FastAPI](https://fastapi.tiangolo.com/) + [uvicorn](https://www.uvicorn.org/) |
| AI backend | [OpenRouter](https://openrouter.ai/) (single API key for all providers) |
| SSE streaming | Server-sent events via FastAPI `StreamingResponse` |
| Claude Code plugin | Skills-directory plugin with `SKILL.md` instructions |

---

## Project Structure

```
polymind/                          ← Python agent
├── pyproject.toml
├── .venv/                         ← virtual environment
└── src/polymind/
    ├── cli.py                     ← argparse, subcommands
    ├── config.py                  ← provider detection (env vars, CLI tools)
    ├── models.py                  ← dataclasses for responses / output
    ├── orchestrator.py            ← parallel API orchestration + tmux + SSE generator
    ├── debate.py                  ← multi-round debate logic
    ├── renderer.py                ← rich terminal output + markdown export
    ├── providers/
    │   ├── base.py                ← Provider ABC, OpenRouter provider with SSE streaming
    │   ├── openai.py              ← OpenAI lane (openrouter/free)
    │   ├── gemini.py              ← Gemini lane (openrouter/free)
    │   ├── grok.py                ← Grok lane (openrouter/free)
    │   └── perplexity.py          ← Perplexity lane (openrouter/free)
    └── web/                       ← Web UI
        ├── __init__.py
        ├── server.py              ← FastAPI app (SSE streaming, status, static files)
        └── static/
            ├── index.html         ← Chat UI layout
            ├── style.css          ← Dark theme, responsive grid
            └── app.js             ← SSE client, provider panel management

.claude/skills/polymind/           ← Claude Code plugin
├── .claude-plugin/plugin.json     ← manifest
├── bin/polymind                   ← PATH shim → project venv
└── skills/
    ├── ask/SKILL.md               ← /polymind:ask command
    └── status/SKILL.md            ← /polymind:status command
```

---

## Setup

### 1. Install the Python agent

```bash
# From the project root (where this README lives):
pip install -e ./polymind
```

Or use the bundled virtualenv:

```bash
python3 -m venv polymind/.venv
polymind/.venv/bin/pip install -e polymind
```

### 2. Set OpenRouter API key

All providers route through [OpenRouter](https://openrouter.ai/). One key covers all four lanes:

```bash
export OPENROUTER_API_KEY="sk-or-..."
```

Add it to your `~/.bashrc`, `~/.zshrc`, or `.env` file.

**Free tier** — all four lanes default to `openrouter/free` which auto-routes to available free models at no cost. Override any lane via env vars when you want a specific paid model:

```bash
# Upgrade to paid models when you have credits
export POLYMIND_MODEL_OPENAI="openai/gpt-4o"
export POLYMIND_MODEL_GEMINI="google/gemini-2.5-flash"
export POLYMIND_MODEL_GROK="x-ai/grok-4.3"
export POLYMIND_MODEL_PERPLEXITY="perplexity/sonar-pro"
```

See the [OpenRouter model list](https://openrouter.ai/models) for all available models.

### 3. Claude Code plugin (optional)

The plugin at `.claude/skills/polymind/` auto-loads when Claude Code starts from this project directory. No install step needed.

---

## Web UI

Start a local web server for a browser-based chat interface:

```bash
polymind web
# → http://localhost:8080
```

Custom host/port:

```bash
polymind web --port 9090 --host 0.0.0.0
```

**Features:**
- Dark-themed chat interface with conversation history
- 4 side-by-side provider panels that stream tokens in real time (SSE)
- Toggle individual providers on/off per message
- Attach code snippets for multi-AI review
- Select review roles (security, performance, simplicity, maintainability)
- Provider status indicators at the top of the page
- Responsive layout — collapses to 2 columns on tablet, 1 column on mobile

---

## Usage

### Standalone terminal

```bash
# Basic query (all configured providers)
polymind ask "What is the best Rust web framework?"

# Specific providers
polymind ask --providers openai,grok "Rust vs Go for microservices?"

# Code review with a file
polymind ask --file src/main.py --roles security,performance "Review this code"

# Debate mode (two rounds with cross-critique)
polymind ask --debate "Should I use SQLite or PostgreSQL?"

# Summary only (hide full responses)
polymind ask --summary-only "What caching strategy should I use?"

# Save to markdown report
polymind ask --save "Explain zero-copy in Rust"

# Save with explicit filename
polymind ask --save report.md "What is the CAP theorem?"

# Stream into a tmux side pane
polymind ask --tmux "Best practices for error handling"

# JSON output (for scripting / Claude Code)
polymind ask --format json "What is Rust?" | jq '.responses[].content'

# Check provider status
polymind status
polymind status --json
```

### Claude Code commands

```
/polymind:status
/polymind:ask What is Rust?
/polymind:ask --providers openai,grok Best error handling patterns?
/polymind:ask --file src/main.py --roles security,performance Review this
/polymind:ask --save --summary-only What database should I use?
/polymind:ask --debate PostgreSQL vs SQLite?
```

---

## Command Reference

### `polymind ask <question> [options]`

| Option | Description |
|---|---|
| `--providers` | Comma-separated: `openai,gemini,grok,perplexity` (default: all configured) |
| `--file <path>` | Include a file's contents for review |
| `--roles` | Code review lenses: `security,performance,simplicity,maintainability` |
| `--save [path]` | Save output to markdown (auto-generated filename if no path given) |
| `--summary-only` | Show only the agreement/disagreement/safest summary |
| `--debate` | Two-round debate: answers → cross-critique → synthesis |
| `--tmux` | Stream responses into a tmux side pane |
| `--format` | Output format: `rich` (default) or `json` |

### `polymind status`

| Option | Description |
|---|---|
| `--json` | Output as JSON (default: rich table) |

### `polymind web`

| Option | Description |
|---|---|
| `--host` | Host to bind (default: `127.0.0.1`) |
| `--port` | Port to bind (default: `8080`) |

---

## Provider Configuration

| Lane | Env Var | Default Model (free) | Override |
|---|---|---|---|
| openai | `OPENROUTER_API_KEY` | `openrouter/free` | `POLYMIND_MODEL_OPENAI` |
| gemini | `OPENROUTER_API_KEY` | `openrouter/free` | `POLYMIND_MODEL_GEMINI` |
| grok | `OPENROUTER_API_KEY` | `openrouter/free` | `POLYMIND_MODEL_GROK` |
| perplexity | `OPENROUTER_API_KEY` | `openrouter/free` | `POLYMIND_MODEL_PERPLEXITY` |

All four lanes share the same `OPENROUTER_API_KEY` and default to free models. Set any `POLYMIND_MODEL_*` env var to switch a lane to a specific model.

---

## Code Review Roles

When `--file` and `--roles` are used together, the question sent to each provider includes the file content and a role-specific prompt:

| Role | Evaluates |
|---|---|
| `security` | Injection risks, auth gaps, unsafe patterns, input validation |
| `performance` | Time complexity, unnecessary allocations, cache misses, bottlenecks |
| `simplicity` | Over-engineering, unnecessary abstraction, cognitive load |
| `maintainability` | Coupling, testability, documentation needs, extensibility |

---

## Output

### Web UI

Each message in the chat shows:
- Your question (with code attachment badge if applicable)
- 4 provider panels with live token streaming
- Spinner while a provider is generating, checkmark on completion, error icon on failure
- Duration footer on each completed panel

### Standalone (rich mode)

- Each provider's response in a colored panel with model name and duration
- Summary table: word counts, character counts, timing
- Areas of agreement (keyword-based topic detection)
- Safest choice recommendation

### Claude Code (plugin mode)

- Labeled sections per provider with model info and timing
- Claude-generated analysis:
  - **Where They Agree** — specific points of convergence
  - **Where They Disagree** — specific differences
  - **Safest Choice** — most conservative recommendation with reasoning
- If `--roles` was used: role-based scoring table

### JSON mode

```json
{
  "meta": { "question": "...", "timestamp": "..." },
  "responses": [
    {
      "provider": "openai",
      "method": "api",
      "model": "gpt-4o",
      "content": "...",
      "error": null,
      "duration_ms": 2345
    }
  ]
}
```

---

## Architecture

```
                    ┌─ Question ────────────────────┐
                    │                                │
                    │  CLI / Claude Code / Web UI    │
                    │           │                    │
                    └───────────┼────────────────────┘
                                │
                                ▼
                    ┌───────────────────────────┐
                    │     polymind CLI / Web     │
                    │                           │
                    │  ┌─────────────────────┐  │
                    │  │ Orchestrator        │  │
                    │  │ (asyncio.gather)    │  │
                    │  │  ├── openai  ──┐   │  │
                    │  │  ├── gemini   ─┤   │  │
                    │  │  ├── grok     ─┤───┤─── OpenRouter
                    │  │  └── perplex  ─┘   │  │
                    │  └─────────────────────┘  │
                    │           │               │
                    │           ▼               │
                    │  ┌─────────────────────┐  │
                    │  │ Renderer            │  │
                    │  │  rich / JSON / SSE  │  │
                    │  │  + tmux (optional)  │  │
                    │  └─────────────────────┘  │
                    └───────┬───────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
    ┌──────────────┐ ┌──────────┐ ┌─────────────┐
    │  Terminal    │ │  Web UI  │ │  Claude     │
    │  (rich/JSON) │ │(browser) │ │  Code       │
    └──────────────┘ └──────────┘ └─────────────┘
```

---

## Development

```bash
# Editable install (changes take effect immediately)
pip install -e ./polymind

# Run tests
cd polymind
python -m pytest   # (add tests/)
```

---

## Troubleshooting

**"No AI providers available"**
→ Set `OPENROUTER_API_KEY` (see [Setup](#2-set-openrouter-api-key))

**"401 Unauthorized"**
→ Your OpenRouter key is invalid or out of credits. Check the env var value or top up at openrouter.ai.

**"polymind: command not found"**
→ `pip install -e ./polymind` didn't complete, or the venv isn't activated. Run `polymind/.venv/bin/polymind status` directly.

**Plugin not showing in Claude Code**
→ Claude Code must be started from this project directory (project-scope plugin). Or run `/reload-plugins` if Claude was already running.
