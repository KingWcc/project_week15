"""FastAPI backend for the LangGraph implementation (default port 8000)."""

from __future__ import annotations

from common.api import create_app

from .pipeline import run_pipeline

app = create_app(
    title="情感支持作业 - LangGraph",
    framework="langgraph",
    runner=run_pipeline,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "langgraph_app.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
