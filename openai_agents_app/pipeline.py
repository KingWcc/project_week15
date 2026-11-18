"""OpenAI Agents SDK version: backend sequentially runs process 1 then process 2.

Agents
------
* 情感识别进程 (process 1)
* 鼓励进程 / 排解进程 / 陪伴进程 (process 2 routes)

The backend is intentionally the orchestrator: it awaits ``Runner.run`` for
process 1, parses the structured result, then passes that result to the selected
process-2 agent.  This mirrors the assignment's "backend chains both processes"
requirement and keeps the branch observable/testable.
"""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

from agents import Agent, ModelSettings, RunConfig, Runner
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

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
from common.schemas import ROUTE_BY_LABEL, ChatResponse

_AGENT_KEYS = {
    "positive": "encourage_agent",
    "negative": "comfort_agent",
    "neutral": "neutral_agent",
}


def _run_config() -> RunConfig:
    # The SDK otherwise tries to export traces to OpenAI, which is unnecessary
    # here and fails when using a DeepSeek-compatible base URL.
    return RunConfig(
        tracing_disabled=True,
        workflow_name="week15-sentiment-support",
        trace_include_sensitive_data=False,
    )


@lru_cache(maxsize=1)
def _get_model() -> OpenAIChatCompletionsModel:
    settings = get_settings()
    client = AsyncOpenAI(
        api_key=settings.require_api_key(),
        base_url=settings.base_url,
        timeout=settings.request_timeout,
        max_retries=1,
    )
    return OpenAIChatCompletionsModel(
        model=settings.model,
        openai_client=client,
    )


@lru_cache(maxsize=1)
def _get_agents() -> dict[str, Agent]:
    model = _get_model()

    sentiment_agent = Agent(
        name="情感识别进程",
        instructions=SENTIMENT_SYSTEM_PROMPT,
        model=model,
        model_settings=ModelSettings(temperature=0.0),
    )
    encourage_agent = Agent(
        name="鼓励进程",
        instructions=REPLY_SYSTEM_PROMPTS["positive"],
        model=model,
        model_settings=ModelSettings(temperature=0.7),
    )
    comfort_agent = Agent(
        name="排解进程",
        instructions=REPLY_SYSTEM_PROMPTS["negative"],
        model=model,
        model_settings=ModelSettings(temperature=0.7),
    )
    neutral_agent = Agent(
        name="陪伴进程",
        instructions=REPLY_SYSTEM_PROMPTS["neutral"],
        model=model,
        model_settings=ModelSettings(temperature=0.7),
    )
    return {
        "sentiment_agent": sentiment_agent,
        "encourage_agent": encourage_agent,
        "comfort_agent": comfort_agent,
        "neutral_agent": neutral_agent,
    }


async def _run_agent(agent: Agent, user_input: str) -> str:
    result = await Runner.run(
        agent,
        input=user_input,
        max_turns=2,
        run_config=_run_config(),
    )
    output: Any = result.final_output
    text = output if isinstance(output, str) else (str(output) if output is not None else "")
    if not text.strip():
        raise ModelResponseError(f"{agent.name} 返回了空内容。")
    return text.strip()


async def run_pipeline(message: str) -> ChatResponse:
    """Backend entry point: process 1 -> branch -> process 2."""
    started = time.perf_counter()
    settings = get_settings()

    if settings.is_mock:
        sentiment = analyze_mock(message)
    else:
        raw_result = await _run_agent(
            _get_agents()["sentiment_agent"],
            build_sentiment_input(message),
        )
        try:
            sentiment = parse_sentiment(raw_result)
        except ValueError as exc:
            raise ModelResponseError(str(exc)) from exc

    route = ROUTE_BY_LABEL[sentiment.label]

    if settings.is_mock:
        reply = build_mock_reply(message, sentiment.label)
    else:
        reply_agent = _get_agents()[_AGENT_KEYS[sentiment.label]]
        reply = await _run_agent(
            reply_agent,
            build_reply_input(message, sentiment),
        )

    return ChatResponse(
        framework="openai-agents",
        mode=settings.mode,
        sentiment=sentiment,
        route=route,
        reply=reply,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )
