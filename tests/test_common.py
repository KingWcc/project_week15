from __future__ import annotations

import os
import unittest

os.environ["LLM_MODE"] = "mock"

from common.mock import analyze_mock  # noqa: E402
from common.parsing import extract_json_object, parse_sentiment  # noqa: E402
from common.schemas import SentimentResult  # noqa: E402


class ParsingTests(unittest.TestCase):
    def test_parses_fenced_json_and_chinese_label(self) -> None:
        raw = """```json
        {"label": "正面", "confidence": 95, "reason": "表达了升职的喜悦"}
        ```"""
        result = parse_sentiment(raw)
        self.assertEqual(result.label, "positive")
        self.assertAlmostEqual(result.confidence, 0.95)
        self.assertIn("升职", result.reason)

    def test_parses_json_after_preamble(self) -> None:
        raw = '分析如下：{"label":"negative","confidence":0.8,"reason":"压力很大"} 完毕'
        result = parse_sentiment(raw)
        self.assertEqual(result.label, "negative")
        self.assertAlmostEqual(result.confidence, 0.8)

    def test_missing_label_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_sentiment('{"confidence":0.8,"reason":"缺少标签"}')

    def test_non_json_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            extract_json_object("今天心情不错")

    def test_schema_rejects_bad_label(self) -> None:
        with self.assertRaises(Exception):
            SentimentResult(label="angry", confidence=0.8, reason="test")


class MockSentimentTests(unittest.TestCase):
    def test_positive(self) -> None:
        result = analyze_mock("今天升职了，太开心了，感觉一切都很顺利！")
        self.assertEqual(result.label, "positive")
        self.assertGreater(result.confidence, 0.7)

    def test_negative(self) -> None:
        result = analyze_mock("最近工作压力好大，好累，也很焦虑。")
        self.assertEqual(result.label, "negative")

    def test_negated_positive_is_not_positive(self) -> None:
        result = analyze_mock("今天真的很不开心。")
        self.assertEqual(result.label, "negative")

    def test_neutral(self) -> None:
        result = analyze_mock("周末打算把房间收拾一下，然后去超市。")
        self.assertEqual(result.label, "neutral")


if __name__ == "__main__":
    unittest.main()
