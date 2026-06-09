import asyncio
import sys
from collections.abc import Callable
from typing import AsyncIterator

from polymind.models import PolymindOutput, ProviderResponse, StreamEvent
from polymind.config import ProviderConfig
from polymind.providers import get_provider


async def run_provider_stream(
    provider_config: ProviderConfig,
    question: str,
    on_event: Callable[[StreamEvent], None] | None = None,
) -> ProviderResponse:
    provider = get_provider(provider_config.name, provider_config)
    if provider is None:
        return ProviderResponse(
            provider=provider_config.name,
            method="—",
            model="—",
            content="",
            error=f"Unknown provider: {provider_config.name}",
            duration_ms=0,
        )

    if not provider.configured:
        return ProviderResponse(
            provider=provider.name,
            method="—",
            model="—",
            content="",
            error="Not configured. Set OPENROUTER_API_KEY.",
            duration_ms=0,
        )

    tokens: list[str] = []
    error: str | None = None
    import time
    start = time.monotonic()

    try:
        async for token in provider.query(question):
            tokens.append(token)
            if on_event:
                on_event(StreamEvent.token(provider.name, token))
    except Exception as e:
        error = str(e)

    duration = int((time.monotonic() - start) * 1000)

    if on_event:
        if error:
            on_event(StreamEvent.error(provider.name, error))
        else:
            on_event(StreamEvent.done(provider.name))

    return ProviderResponse(
        provider=provider.name,
        method=provider.method,
        model=provider._model_name(),
        content="".join(tokens),
        error=error,
        duration_ms=duration,
    )


async def ask(
    question: str,
    providers: list[ProviderConfig],
    file_content: str | None = None,
    roles: list[str] | None = None,
    on_event: Callable[[StreamEvent], None] | None = None,
) -> PolymindOutput:
    effective_question = question

    if file_content and roles:
        effective_question = (
            f"Review this code for {', '.join(roles)}:\n\n"
            f"```\n{file_content}\n```\n\n"
            f"{question}"
        )
    elif file_content:
        effective_question = (
            f"Review this code:\n\n```\n{file_content}\n```\n\n"
            f"{question}"
        )
    elif roles:
        effective_question = (
            f"Answer the following considering {', '.join(roles)}:\n\n"
            f"{question}"
        )

    tasks = [
        run_provider_stream(pc, effective_question, on_event)
        for pc in providers
    ]
    results = await asyncio.gather(*tasks)

    output = PolymindOutput(question=question, responses=list(results))
    return output


async def stream_ask(
    question: str,
    providers: list[ProviderConfig],
    file_content: str | None = None,
    roles: list[str] | None = None,
) -> AsyncIterator[StreamEvent]:
    """Like ask(), but yields StreamEvents as they happen (for SSE streaming)."""
    if not providers:
        yield StreamEvent("error", "system", "No providers configured. Set OPENROUTER_API_KEY.")
        return

    queue: asyncio.Queue[StreamEvent] = asyncio.Queue()

    def on_event(event: StreamEvent):
        queue.put_nowait(event)

    ask_task = asyncio.create_task(
        ask(question, providers, file_content, roles, on_event=on_event)
    )

    finished: set[str] = set()
    provider_count = len(providers)

    while len(finished) < provider_count:
        event = await queue.get()
        yield event
        if event.kind in ("done", "error"):
            finished.add(event.provider)

    await ask_task


async def run_in_tmux(
    question: str,
    providers: list[ProviderConfig],
    file_content: str | None = None,
    roles: list[str] | None = None,
) -> PolymindOutput:
    import tempfile

    log_fd, log_path = tempfile.mkstemp(suffix=".polymind.log", prefix="polymind-")
    import os
    os.close(log_fd)

    import subprocess
    subprocess.run(
        ["tmux", "split-window", "-h",
         f"tail -f {log_path} 2>/dev/null; echo '— polymind: all responses received —'; sleep 10"],
        capture_output=True,
    )

    tmux_pane = os.environ.get("TMUX_PANE", "?")

    def log_event(event: StreamEvent):
        with open(log_path, "a") as f:
            label = {"token": ">", "done": "✓", "error": "✗", "summary": "="}.get(
                event.kind, "?"
            )
            f.write(f"[{event.provider}] {label} {event.data}\n")

    result = await ask(question, providers, file_content, roles, on_event=log_event)

    with open(log_path, "a") as f:
        f.write("\n=== All responses received ===\n")
        for r in result.responses:
            status = "OK" if not r.error else f"ERROR: {r.error}"
            f.write(f"[{r.provider}] {status} ({r.duration_ms}ms, {len(r.content)} chars)\n")

    return result
