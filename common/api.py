"""FastAPI app factory shared by the LangGraph and Agents SDK backends."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_DIR, ConfigurationError, get_settings
from .errors import ModelResponseError
from .schemas import ChatRequest, ChatResponse, Framework

PipelineRunner = Callable[[str], Awaitable[ChatResponse]]


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "*")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["*"]


def create_app(
    *,
    title: str,
    framework: Framework,
    runner: PipelineRunner,
) -> FastAPI:
    """Create a backend with health, chat and static-frontend endpoints."""

    logger = logging.getLogger(f"week15.{framework}")
    app = FastAPI(
        title=title,
        version="1.0.0",
        description=f"{framework} 版本：两个 Agent 串联的情感支持服务。",
    )

    origins = _cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials="*" not in origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    if FRONTEND_DIR.is_dir():
        app.mount(
            "/static",
            StaticFiles(directory=str(FRONTEND_DIR)),
            name="static",
        )

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        index_file = FRONTEND_DIR / "index.html"
        if not index_file.is_file():
            raise HTTPException(status_code=404, detail="前端页面不存在。")
        return FileResponse(index_file)

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        try:
            settings = get_settings()
        except ConfigurationError as exc:
            return {
                "status": "error",
                "framework": framework,
                "detail": str(exc),
            }

        ready = settings.is_mock or settings.is_configured
        return {
            "status": "ok" if ready else "degraded",
            "framework": framework,
            **settings.public_dict(),
        }

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        try:
            settings = get_settings()
        except ConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        # The model client already has a per-request timeout; this outer guard
        # also covers queueing / slow framework overhead.
        timeout = settings.request_timeout + 5.0
        try:
            return await asyncio.wait_for(runner(request.message), timeout=timeout)
        except ConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail="模型响应超时，请稍后重试或缩短输入内容。",
            ) from exc
        except ModelResponseError as exc:
            logger.warning("Model response rejected: %s", exc)
            raise HTTPException(
                status_code=502,
                detail="模型返回内容无法解析，请重试一次。",
            ) from exc
        except Exception:
            logger.exception("Unhandled pipeline error (%s)", framework)
            raise HTTPException(
                status_code=502,
                detail="模型服务调用失败，请检查网络、API Key 和模型配置。",
            ) from None

    return app
