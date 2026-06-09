from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich.columns import Columns

from polymind.models import PolymindOutput, ProviderResponse
from polymind.config import status_report

PROVIDER_COLORS = {
    "openai": "green",
    "gemini": "blue",
    "grok": "magenta",
    "perplexity": "cyan",
}

console = Console()


def render_status():
    rows = status_report()
    table = Table(title="Polymind — Provider Status", border_style="bright_blue")
    table.add_column("Provider", style="bold")
    table.add_column("Status")
    table.add_column("Model")
    table.add_column("Detail")

    for row in rows:
        status_icon = "✅" if row["available"] else "❌"
        table.add_row(
            row["provider"],
            status_icon,
            row["model"],
            row["detail"],
        )

    console.print(table)


def render_output(output: PolymindOutput, summary_only: bool = False, save_path: str | None = None):
    if not summary_only:
        cols = Columns(equal=False, expand=True)
        panel_group = []

        for r in output.responses:
            color = PROVIDER_COLORS.get(r.provider, "white")
            if r.error:
                content = Text(f"[Error] {r.error}", style="red")
            else:
                content = Text(r.content[:2000], style=color)
                if len(r.content) > 2000:
                    content.append(f"\n\n... ({len(r.content) - 2000} more chars)", style="dim")
            panel = Panel(
                content,
                title=f"[bold]{r.provider.upper()}[/]",
                subtitle=f"{r.model} | {r.duration_ms}ms" if not r.error else "failed",
                border_style=color,
                padding=(1, 2),
            )
            panel_group.append(panel)

        console.print(Columns(panel_group, equal=False))
        console.print()

    if output.responses:
        render_summary(output)

    if save_path:
        _save_markdown(output, save_path)


def render_summary(output: PolymindOutput):
    console.print(Rule(style="bright_yellow"))
    console.print(Text("Summary", style="bold bright_yellow"))
    console.print()

    responses = output.responses
    if not responses:
        console.print(Text("No responses to summarize.", style="dim"))
        return

    successful = [r for r in responses if not r.error]
    failed = [r for r in responses if r.error]

    table = Table(border_style="yellow")
    table.add_column("Metric")
    for r in successful:
        color = PROVIDER_COLORS.get(r.provider, "white")
        table.add_column(r.provider.upper(), style=color)
    table.add_column("Consensus")

    word_counts = {r.provider: len(r.content.split()) for r in successful}
    chars = {r.provider: len(r.content) for r in successful}
    durations = {r.provider: f"{r.duration_ms}ms" for r in successful}

    table.add_row("Words",
                  *[str(word_counts[r.provider]) for r in successful],
                  str(sum(word_counts.values()) // max(len(successful), 1)))
    table.add_row("Chars",
                  *[str(chars[r.provider]) for r in successful],
                  str(sum(chars.values())))
    table.add_row("Duration",
                  *[durations[r.provider] for r in successful],
                  "")

    console.print(table)
    console.print()

    if failed:
        console.print(Text("Failed providers:", style="bold red"))
        for r in failed:
            console.print(f"  [{r.provider}] {r.error}")
        console.print()

    _render_agreement(output, successful)


def _render_agreement(output: PolymindOutput, successful: list[ProviderResponse]):
    if len(successful) < 2:
        return

    texts = [(r.provider, r.content.lower()) for r in successful]

    common_topics = _find_common_topics(texts)

    console.print(Text("Areas of Agreement", style="bold green"))
    if common_topics:
        for topic in common_topics[:5]:
            mentioned_by = ", ".join(t[0] for t in texts if topic in t[1])
            console.print(f"  ✓ \"{topic}\" mentioned by {mentioned_by}")
    else:
        console.print("  (automatic topic detection limited — providers may agree on specifics not captured here)")
    console.print()

    console.print(Text("Safest Choice", style="bold yellow"))
    console.print(
        "  The most conservative approach is to adopt recommendations shared across "
        "most providers. Consider the tradeoffs each response highlights for your specific context."
    )
    console.print()


def _find_common_topics(texts: list[tuple[str, str]], min_providers: int = 2) -> list[str]:
    from collections import Counter
    import re

    all_words: list[str] = []
    for _, text in texts:
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text)
        all_words.extend(words)

    word_freq = Counter(all_words)

    common = []
    for _, text in texts:
        for word, count in word_freq.most_common(100):
            if count >= min_providers and count < len(texts) * 3:
                mentions = sum(1 for _, t in texts if word in t)
                if mentions >= min_providers:
                    common.append(word)

    seen = set()
    unique_common = []
    for w in common:
        if w not in seen:
            seen.add(w)
            unique_common.append(w)

    return unique_common[:10]


def _save_markdown(output: PolymindOutput, path: str):
    lines = []
    lines.append(f"# Polymind Report\n")
    lines.append(f"**Question:** {output.question}\n")
    lines.append(f"**Timestamp:** {output.timestamp}\n")
    lines.append("---\n")

    for r in output.responses:
        lines.append(f"## {r.provider.upper()} ({r.model})\n")
        lines.append(f"*{r.duration_ms}ms | {len(r.content.split())} words*\n")
        if r.error:
            lines.append(f"> Error: {r.error}\n")
        else:
            lines.append(r.content)
        lines.append("\n---\n")

    successful = [r for r in output.responses if not r.error]
    if successful:
        lines.append("## Summary\n")
        for r in successful:
            lines.append(f"- **{r.provider}**: {len(r.content.split())} words, {r.duration_ms}ms\n")

    content = "\n".join(lines)
    with open(path, "w") as f:
        f.write(content)
    console.print(f"Saved to [bold]{path}[/]")
