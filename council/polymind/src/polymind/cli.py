import argparse
import asyncio
import os
import sys
import json
from datetime import datetime

from polymind.config import get_available_providers, status_report
from polymind.orchestrator import ask, run_in_tmux
from polymind.renderer import render_output, render_status


def main():
    parser = argparse.ArgumentParser(
        prog="polymind",
        description="Query multiple AI coding assistants at once",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ask_p = sub.add_parser("ask", help="Ask a question to multiple AI providers")
    ask_p.add_argument("question", nargs="*", help="Your question")
    ask_p.add_argument("--providers", help="Comma-separated: openai,gemini,grok,perplexity")
    ask_p.add_argument("--file", help="Include a file for review")
    ask_p.add_argument("--roles", help="Comma-separated: security,performance,simplicity,maintainability")
    ask_p.add_argument("--save", nargs="?", const="auto", default=None, help="Save output to a markdown file (path or auto)")
    ask_p.add_argument("--summary-only", action="store_true", help="Show only the summary")
    ask_p.add_argument("--debate", action="store_true", help="Run a multi-round debate")
    ask_p.add_argument("--tmux", action="store_true", help="Stream results into a tmux side pane")
    ask_p.add_argument("--format", choices=["rich", "json"], default="rich", help="Output format")

    status_p = sub.add_parser("status", help="Show which providers are configured")
    status_p.add_argument("--json", action="store_true", help="Output as JSON")

    web_p = sub.add_parser("web", help="Start the Polymind web UI")
    web_p.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    web_p.add_argument("--port", type=int, default=8080, help="Port to bind (default: 8080)")

    args = parser.parse_args()

    if args.command == "status":
        if args.json:
            print(json.dumps(status_report(), indent=2))
        else:
            render_status()
        return

    if args.command == "web":
        from polymind.web.server import run
        run(host=args.host, port=args.port)
        return

    question = " ".join(args.question) if args.question else ""
    if not question:
        question = sys.stdin.read().strip()
    if not question:
        print("Error: no question provided", file=sys.stderr)
        sys.exit(1)

    provider_names = [p.strip() for p in args.providers.split(",")] if args.providers else None
    providers = get_available_providers(provider_names)

    if not providers:
        print("No AI providers available.", file=sys.stderr)
        print("Set OPENROUTER_API_KEY to use all providers via OpenRouter.", file=sys.stderr)
        sys.exit(1)

    file_content = None
    if args.file:
        try:
            with open(args.file) as f:
                file_content = f.read()
        except Exception as e:
            print(f"Error reading file {args.file}: {e}", file=sys.stderr)
            sys.exit(1)

    roles = [r.strip() for r in args.roles.split(",")] if args.roles else None

    if args.tmux and os.environ.get("TMUX"):
        if args.format == "json":
            print("Warning: --tmux and --format json together may produce mixed output", file=sys.stderr)
        output = asyncio.run(run_in_tmux(question, providers, file_content, roles))
    else:
        output = asyncio.run(ask(question, providers, file_content, roles))

    if args.debate and not args.tmux:
        from polymind.debate import run_debate
        output = asyncio.run(run_debate(output, providers))

    save_path = None
    if args.save:
        path = args.save
        if path == "auto":
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            path = f"polymind-{ts}.md"
        save_path = path

    if args.format == "json":
        print(json.dumps(output.to_dict(), indent=2))
        if save_path:
            render_output(output, save_path=save_path)
    else:
        render_output(output, summary_only=args.summary_only, save_path=save_path)
