"""FastAPI backend for the OpenAI Agents SDK implementation (default port 8001)."""

from __future__ import annotations

from common.api import create_app

from .pipeline import run_pipeline

app = create_app(
    title="情感支持作业 - OpenAI Agents",
    framework="openai-agents",
    runner=run_pipeline,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "openai_agents_app.server:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
    )
