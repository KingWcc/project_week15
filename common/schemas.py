"""Pydantic contracts shared by the backend, frontend and both frameworks."""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SentimentLabel = Literal["positive", "negative", "neutral"]
Route = Literal["encourage", "comfort", "neutral"]
Framework = Literal["langgraph", "openai-agents"]

ROUTE_BY_LABEL: dict[SentimentLabel, Route] = {
    "positive": "encourage",
    "negative": "comfort",
    "neutral": "neutral",
}
ROUTE_NODE_NAMES: dict[Route, str] = {
    "encourage": "process2_encourage",
    "comfort": "process2_comfort",
    "neutral": "process2_neutral",
}

_LABEL_ALIASES = {
    "positive": "positive",
    "positve": "positive",
    "正面": "positive",
    "积极": "positive",
    "正向": "positive",
    "negative": "negative",
    "negitive": "negative",
    "负面": "negative",
    "消极": "negative",
    "负向": "negative",
    "neutral": "neutral",
    "neutural": "neutral",
    "中性": "neutral",
    "中立": "neutral",
    "mixed": "neutral",
    "混合": "neutral",
}


def normalize_label(value: Any) -> SentimentLabel:
    key = str(value).strip().lower()
    normalized = _LABEL_ALIASES.get(key)
    if normalized is None:
        raise ValueError(
            f"未知情感标签 {value!r}；只允许 positive / negative / neutral。"
        )
    return normalized  # type: ignore[return-value]


class SentimentResult(BaseModel):
    """Structured output of process 1 (sentiment recognition)."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    label: SentimentLabel
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("label", mode="before")
    @classmethod
    def _normalize_label(cls, value: Any) -> SentimentLabel:
        return normalize_label(value)

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, value: Any) -> float:
        if isinstance(value, bool):
            raise ValueError("confidence 必须是数字。")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("confidence 必须是 0 到 1 之间的数字。") from exc
        if not math.isfinite(number):
            raise ValueError("confidence 必须是有限数字。")
        # Some models answer "95" for 95%; accept that common convention.
        if 1.0 < number <= 100.0:
            number /= 100.0
        if not 0.0 <= number <= 1.0:
            raise ValueError("confidence 必须在 0 到 1 之间。")
        return number

    @field_validator("reason", mode="before")
    @classmethod
    def _normalize_reason(cls, value: Any) -> str:
        text = str(value).strip() if value is not None else ""
        return text or "模型未提供具体理由。"


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def _non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("输入内容不能为空。")
        return value


class ChatResponse(BaseModel):
    framework: Framework
    mode: Literal["llm", "mock"]
    sentiment: SentimentResult
    route: Route
    reply: str
    elapsed_ms: int
