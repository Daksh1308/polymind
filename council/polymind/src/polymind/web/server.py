import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from polymind.config import get_available_providers, status_report
from polymind.orchestrator import stream_ask

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Polymind")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
async def api_status():
    return status_report()


@app.post("/api/chat")
async def chat(body: dict):
    question = body.get("question", "").strip()
    if not question:
        return StreamingResponse(
            iter(['data: {"kind":"error","provider":"system","data":"No question provided"}\n\n']),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    provider_names = None
    raw = body.get("providers")
    if raw:
        provider_names = [p.strip() for p in raw.split(",") if p.strip()]

    provider_configs = get_available_providers(provider_names)
    file_content = body.get("file_content") or None
    roles = body.get("roles") or None

    async def event_stream():
        async for event in stream_ask(question, provider_configs, file_content, roles):
            data = json.dumps({"kind": event.kind, "provider": event.provider, "data": event.data})
            yield f"data: {data}\n\n"
        yield "data: {\"kind\":\"complete\"}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def run(host: str = "127.0.0.1", port: int = 8080):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")
