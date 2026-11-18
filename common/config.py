"""Runtime configuration shared by both framework implementations.

The code deliberately supports the DeepSeek OpenAI-compatible endpoint as well
as a real OpenAI endpoint.  Secrets are only ever read from environment
variables; they are never written to disk by the application.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# Load a project-local .env when present.  Existing environment variables always
# win, which is important for Docker and CI deployments.
load_dotenv(PROJECT_ROOT / ".env", override=False)


class ConfigurationError(RuntimeError):
    """Raised when required model configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    mode: str
    api_key: str | None
    base_url: str
    model: str
    request_timeout: float

    @property
    def is_mock(self) -> bool:
        return self.mode == "mock"

    @property
    def is_configured(self) -> bool:
        return self.api_key is not None

    def require_api_key(self) -> str:
        if not self.api_key:
            raise ConfigurationError(
                "未配置模型 API Key。请在 .env 中设置 OPENAI_API_KEY"
                "（或 DEEPSEEK_API_KEY），或将 LLM_MODE 设为 mock 进行离线演示。"
            )
        return self.api_key

    def public_dict(self) -> dict[str, object]:
        """Return diagnostics that are safe to expose through /api/health."""
        return {
            "mode": self.mode,
            "model": self.model,
            "base_url": self.base_url,
            "api_key_configured": self.is_configured,
        }


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def get_settings() -> Settings:
    mode = _env("LLM_MODE", "llm").lower()
    if mode not in {"llm", "mock"}:
        raise ConfigurationError(
            f"LLM_MODE 只能是 'llm' 或 'mock'，当前值为 {mode!r}。"
        )

    api_key = _env("OPENAI_API_KEY") or _env("DEEPSEEK_API_KEY") or None
    base_url = _env("OPENAI_BASE_URL") or _env("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
    model = _env("OPENAI_MODEL") or _env("DEEPSEEK_MODEL") or "deepseek-chat"

    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigurationError(f"模型 BASE_URL 不合法：{base_url!r}")

    raw_timeout = _env("REQUEST_TIMEOUT", "90")
    try:
        request_timeout = float(raw_timeout)
    except ValueError as exc:
        raise ConfigurationError("REQUEST_TIMEOUT 必须是数字（秒）。") from exc
    if request_timeout <= 0:
        raise ConfigurationError("REQUEST_TIMEOUT 必须大于 0。")

    return Settings(
        mode=mode,
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        model=model,
        request_timeout=request_timeout,
    )
