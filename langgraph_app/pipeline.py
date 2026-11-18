"""LangGraph version: process 1 -> conditional edge -> process 2 branch.

Graph topology
--------------

    START
      |
    process1_sentiment
      |  route = encourage / comfort / neutral
      +--> process2_encourage --> END
      +--> process2_comfort   --> END
      +--> process2_neutral   --> END

The backend calls ``run_pipeline`` once; LangGraph performs the fan-out after
process 1 based on the structured sentiment result.
"""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from common.config import get_settings
from common.errors import ModelResponseError
from common.mock import analyze_mock, build_mock_reply
from common.parsing import parse_sentiment
from common.prompts import (
    REPLY_SYSTEM_PROMPTS,
    SENTIMENT_SYSTEM_PROMPT,
    build_reply_input,
    build_sentiment_input,
)
from common.schemas import (
    ROUTE_BY_LABEL,
    ROUTE_NODE_NAMES,
    ChatResponse,
    Route,
    SentimentLabel,
    SentimentResult,
)


class PipelineState(TypedDict, total=False):
    message: str
    sentiment: dict[str, Any]
    route: Route
    reply: str


def _content_to_text(content: Any) -> str:
    """Normalize AIMessage.content across OpenAI-compatible providers."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return str(content) if content is not None else ""


@lru_cache(maxsize=2)
def _get_chat_model(temperature: float) -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.model,
        api_key=settings.require_api_key(),
        base_url=settings.base_url,
        temperature=temperature,
        timeout=settings.request_timeout,
        max_retries=1,
    )


async def process1_sentiment(state: PipelineState) -> dict[str, Any]:
    """Node 1: classify the user's message, without generating a reply."""
    message = state["message"]
    settings = get_settings()

    if settings.is_mock:
        sentiment = analyze_mock(message)
    else:
        try:
            response = await _get_chat_model(0.0).ainvoke(
                [
                    SystemMessage(content=SENTIMENT_SYSTEM_PROMPT),
                    HumanMessage(content=build_sentiment_input(message)),
                ]
            )
            sentiment = parse_sentiment(_content_to_text(response.content))
        except ValueError as exc:
            raise ModelResponseError(str(exc)) from exc

    return {
        "sentiment": sentiment.model_dump(),
        "route": ROUTE_BY_LABEL[sentiment.label],
    }


async def _process2_reply(state: PipelineState, style: SentimentLabel) -> dict[str, Any]:
    message = state["message"]
    try:
        sentiment = SentimentResult.model_validate(state["sentiment"])
    except Exception as exc:
        raise ModelResponseError("进程1的情感结果缺失或不合法。") from exc

    settings = get_settings()
    if settings.is_mock:
        reply = build_mock_reply(message, sentiment.label)
    else:
        response = await _get_chat_model(0.7).ainvoke(
            [
                SystemMessage(content=REPLY_SYSTEM_PROMPTS[style]),
                HumanMessage(content=build_reply_input(message, sentiment)),
            ]
        )
        reply = _content_to_text(response.content).strip()

    if not reply:
        raise ModelResponseError("进程2返回了空回复。")
    return {"reply": reply}


async def process2_encourage(state: PipelineState) -> dict[str, Any]:
    """Node 2a: positive sentiment -> encouragement."""
    return await _process2_reply(state, "positive")


async def process2_comfort(state: PipelineState) -> dict[str, Any]:
    """Node 2b: negative sentiment -> emotional relief."""
    return await _process2_reply(state, "negative")


async def process2_neutral(state: PipelineState) -> dict[str, Any]:
    """Node 2c: neutral sentiment -> companionship."""
    return await _process2_reply(state, "neutral")


def _route_after_process1(state: PipelineState) -> Route:
    route = state.get("route", "neutral")
    return route if route in ROUTE_NODE_NAMES else "neutral"


@lru_cache(maxsize=1)
def build_graph():
    workflow = StateGraph(PipelineState)
    workflow.add_node("process1_sentiment", process1_sentiment)
    workflow.add_node("process2_encourage", process2_encourage)
    workflow.add_node("process2_comfort", process2_comfort)
    workflow.add_node("process2_neutral", process2_neutral)

    workflow.add_edge(START, "process1_sentiment")
    workflow.add_conditional_edges(
        "process1_sentiment",
        _route_after_process1,
        ROUTE_NODE_NAMES,
    )
    for node_name in ROUTE_NODE_NAMES.values():
        workflow.add_edge(node_name, END)

    return workflow.compile(name="sentiment-support-graph")


async def run_pipeline(message: str) -> ChatResponse:
    """Backend entry point: run the graph and adapt state to the API schema."""
    started = time.perf_counter()
    state = await build_graph().ainvoke({"message": message})

    try:
        sentiment = SentimentResult.model_validate(state["sentiment"])
        route = state["route"]
        reply = state["reply"]
    except (KeyError, TypeError) as exc:
        raise ModelResponseError("图执行完成，但缺少情感结果或回复。") from exc
    if route not in ROUTE_NODE_NAMES or not reply:
        raise ModelResponseError("图执行完成，但输出不完整。")

    settings = get_settings()
    return ChatResponse(
        framework="langgraph",
        mode=settings.mode,
        sentiment=sentiment,
        route=route,
        reply=reply,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )
