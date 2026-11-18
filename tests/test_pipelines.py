from __future__ import annotations

import os
import unittest

os.environ["LLM_MODE"] = "mock"

from langgraph_app.pipeline import run_pipeline as run_langgraph  # noqa: E402
from openai_agents_app.pipeline import run_pipeline as run_agents  # noqa: E402


class LangGraphPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_positive_routes_to_encouragement(self) -> None:
        result = await run_langgraph("今天终于拿到了心仪的 offer，太开心了！")
        self.assertEqual(result.framework, "langgraph")
        self.assertEqual(result.mode, "mock")
        self.assertEqual(result.sentiment.label, "positive")
        self.assertEqual(result.route, "encourage")
        self.assertTrue(result.reply)
        self.assertGreaterEqual(result.elapsed_ms, 0)

    async def test_negative_routes_to_comfort(self) -> None:
        result = await run_langgraph("最近压力好大，晚上总是睡不着，很难受。")
        self.assertEqual(result.sentiment.label, "negative")
        self.assertEqual(result.route, "comfort")
        self.assertIn("你", result.reply)


class OpenAIAgentsPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_positive_routes_to_encouragement(self) -> None:
        result = await run_agents("今天升职加薪了，真的太开心了！")
        self.assertEqual(result.framework, "openai-agents")
        self.assertEqual(result.mode, "mock")
        self.assertEqual(result.sentiment.label, "positive")
        self.assertEqual(result.route, "encourage")

    async def test_negative_routes_to_comfort(self) -> None:
        result = await run_agents("觉得自己什么都做不好，很焦虑，也很累。")
        self.assertEqual(result.sentiment.label, "negative")
        self.assertEqual(result.route, "comfort")
        self.assertTrue(result.reply)

    async def test_neutral_routes_to_companionship(self) -> None:
        result = await run_agents("周末打算把房间收拾一下，然后去超市。")
        self.assertEqual(result.sentiment.label, "neutral")
        self.assertEqual(result.route, "neutral")


if __name__ == "__main__":
    unittest.main()
