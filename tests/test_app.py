import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app, agent_lock


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_page_and_assets(self):
        for path, content in [("/", "Where are we going?"),
                              ("/static/style.css", "prefers-reduced-motion"),
                              ("/static/script.js", "/api/plan")]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn(content, response.text)

    @patch("app.run_agent")
    def test_calls_existing_agent_and_preserves_response(self, runner):
        result = {"answer": "Your trip", "thread_id": "example", "flight_results": "Flights", "hotel_results": "Hotels"}
        runner.return_value = result
        response = self.client.post("/api/plan", json={"user_input": "  Kochi to Copenhagen  ", "thread_id": "example"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), result)
        runner.assert_called_once_with("Kochi to Copenhagen", "example")

    @patch("app.run_agent")
    def test_rejects_invalid_requests_before_agent_call(self, runner):
        for payload in [{}, {"user_input": "   "}, {"user_input": "x" * 4001}, {"user_input": "Rome", "thread_id": ""}]:
            self.assertEqual(self.client.post("/api/plan", json=payload).status_code, 422)
        runner.assert_not_called()

    @patch("app.run_agent", side_effect=RuntimeError("secret connection string"))
    def test_errors_are_safe_and_release_lock(self, runner):
        response = self.client.post("/api/plan", json={"user_input": "Kochi to Copenhagen"})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("secret", response.text)
        self.assertFalse(agent_lock.locked())

    @patch("app.run_agent")
    def test_busy_agent_does_not_block_health_or_accept_more_work(self, runner):
        agent_lock.acquire()
        try:
            response = self.client.post("/api/plan", json={"user_input": "Kochi to Copenhagen"})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.headers["retry-after"], "10")
            self.assertEqual(self.client.get("/api/health").json(), {"status": "ok"})
            runner.assert_not_called()
        finally:
            agent_lock.release()


if __name__ == "__main__":
    unittest.main()
