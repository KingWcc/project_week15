"""Tolerant parsing of the JSON that process 1 is asked to return."""

from __future__ import annotations

import json
import re
from typing import Any

from .schemas import SentimentResult

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract the first JSON object from plain text or a fenced code block.

    Chat models sometimes wrap JSON in a Markdown fence or add a short preamble
    despite being told not to.  A small fallback keeps the application usable
    without silently inventing a sentiment when no JSON exists.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("模型返回了空内容。")

    candidates = [text.strip()]
    without_fences = _FENCE_RE.sub("", text.strip()).strip()
    if without_fences != candidates[0]:
        candidates.append(without_fences)

    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value

    # Decode from each "{" so a leading explanation ("结果是 {...}") still works.
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", without_fences):
        try:
            value, _ = decoder.raw_decode(without_fences[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value

    raise ValueError("模型没有返回可解析的 JSON 对象。")


def parse_sentiment(text: str) -> SentimentResult:
    data = extract_json_object(text)

    label = data.get("label", data.get("sentiment", data.get("情感")))
    if label is None:
        raise ValueError("情感识别结果缺少 label 字段。")

    confidence = data.get("confidence", data.get("score", data.get("置信度", 0.5)))
    reason = data.get("reason", data.get("explanation", data.get("理由", "")))

    try:
        return SentimentResult(
            label=label,
            confidence=confidence,
            reason=reason,
        )
    except Exception as exc:
        raise ValueError(f"情感识别结果字段不合法：{exc}") from exc
