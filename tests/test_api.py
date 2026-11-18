from __future__ import annotations

import os
import unittest

os.environ["LLM_MODE"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from langgraph_app.server import app as langgraph_app  # noqa: E402
from openai_agents_app.server import app as agents_app  # noqa: E402


class BackendApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clients = [
            ("langgraph", TestClient(langgraph_app)),
            ("openai-agents", TestClient(agents_app)),
        ]

    def test_health_for_both_frameworks(self) -> None:
        for framework, client in self.clients:
            response = client.get("/api/health")
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["framework"], framework)
            self.assertEqual(body["mode"], "mock")
            self.assertEqual(body["status"], "ok")

    def test_frontend_is_served(self) -> None:
        client = self.clients[0][1]
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("心语", response.text)
        self.assertIn("/api/chat", response.text)

    def test_chat_contract_for_both_frameworks(self) -> None:
        for framework, client in self.clients:
            response = client.post(
                "/api/chat",
                json={"message": "今天拿到了心仪的 offer，太开心了！"},
            )
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body["framework"], framework)
            self.assertEqual(body["sentiment"]["label"], "positive")
            self.assertEqual(body["route"], "encourage")
            self.assertTrue(body["reply"])

    def test_blank_message_is_rejected(self) -> None:
        for _, client in self.clients:
            response = client.post("/api/chat", json={"message": "   "})
            self.assertEqual(response.status_code, 422)

    def test_openapi_is_available(self) -> None:
        for _, client in self.clients:
            self.assertEqual(client.get("/openapi.json").status_code, 200)


if __name__ == "__main__":
    unittest.main()
