from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator


@dataclass
class ProviderResponse:
    provider: str
    method: str  # "api" or "cli"
    model: str
    content: str
    error: str | None = None
    duration_ms: int = 0


@dataclass
class DebateRound:
    round: int
    responses: list[ProviderResponse]
    critiques: list[ProviderResponse] | None = None


@dataclass
class PolymindOutput:
    question: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    responses: list[ProviderResponse] = field(default_factory=list)
    debate: list[DebateRound] | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        base = {
            "meta": {
                "question": self.question,
                "timestamp": self.timestamp,
            },
            "responses": [
                {
                    "provider": r.provider,
                    "method": r.method,
                    "model": r.model,
                    "content": r.content,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                }
                for r in self.responses
            ],
            "errors": self.errors,
        }
        if self.debate:
            base["debate"] = [
                {
                    "round": dr.round,
                    "responses": [
                        {
                            "provider": r.provider,
                            "method": r.method,
                            "model": r.model,
                            "content": r.content,
                            "error": r.error,
                        }
                        for r in dr.responses
                    ],
                    "critiques": [
                        {
                            "provider": r.provider,
                            "method": r.method,
                            "model": r.model,
                            "content": r.content,
                            "error": r.error,
                        }
                        for r in (dr.critiques or [])
                    ] if dr.critiques else None,
                }
                for dr in self.debate
            ]
        return base


class StreamEvent:
    """Events emitted during streaming for the renderer to consume."""

    def __init__(self, kind: str, provider: str, data: str = ""):
        self.kind = kind
        self.provider = provider
        self.data = data

    @classmethod
    def token(cls, provider: str, text: str) -> "StreamEvent":
        return cls("token", provider, text)

    @classmethod
    def done(cls, provider: str) -> "StreamEvent":
        return cls("done", provider)

    @classmethod
    def error(cls, provider: str, message: str) -> "StreamEvent":
        return cls("error", provider, message)

    @classmethod
    def summary(cls, provider: str, text: str) -> "StreamEvent":
        return cls("summary", provider, text)
