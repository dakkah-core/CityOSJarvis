"""Locust load test for CityOSJarvis BFF endpoints."""

from locust import HttpUser, task, between
import random
import json


class ChatUser(HttpUser):
    """Simulates a citizen chatting with the AI assistant."""

    wait_time = between(1, 5)
    weight = 3

    def on_start(self):
        self.client.headers["X-Tenant-Id"] = "perf-test"
        self.client.headers["X-Correlation-Id"] = f"perf-{self.user_id}"

    @task(10)
    def send_message(self):
        self.client.post(
            "/api/bff/ai/chat",
            json={
                "message": random.choice([
                    "What's the weather?",
                    "How do I pay my bill?",
                    "Report a pothole",
                    "Book a doctor appointment",
                    "Find parking near me",
                ]),
                "agentId": "default",
                "stream": False,
            },
            timeout=30,
        )

    @task(2)
    def stream_message(self):
        with self.client.post(
            "/api/bff/ai/chat",
            json={
                "message": "Tell me about city services",
                "agentId": "default",
                "stream": True,
            },
            stream=True,
            timeout=60,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                chunks = 0
                for _ in response.iter_content(chunk_size=1024):
                    chunks += 1
                response.success()
            else:
                response.failure(f"Stream failed: {response.status_code}")

    @task(3)
    def list_agents(self):
        self.client.get("/api/bff/ai/agents", timeout=10)

    @task(3)
    def list_models(self):
        self.client.get("/api/bff/ai/models", timeout=10)

    @task(1)
    def health_check(self):
        self.client.get("/api/bff/ai/health", timeout=5)


class VoiceUser(HttpUser):
    """Simulates voice interactions."""

    wait_time = between(2, 8)
    weight = 1

    def on_start(self):
        self.client.headers["X-Tenant-Id"] = "perf-test"

    @task(1)
    def process_intent(self):
        self.client.post(
            "/api/bff/ai/voice/process-intent",
            json={"text": "What's the traffic like?", "language": "en"},
            timeout=15,
        )

    @task(1)
    def tts_synthesis(self):
        self.client.post(
            "/api/bff/ai/voice/speak",
            json={"text": "Welcome to Dakkah CityOS", "voiceId": "default", "language": "en"},
            timeout=10,
        )


class ToolUser(HttpUser):
    """Simulates MCP tool execution."""

    wait_time = between(3, 10)
    weight = 1

    def on_start(self):
        self.client.headers["X-Tenant-Id"] = "perf-test"

    @task(1)
    def execute_weather_tool(self):
        self.client.post(
            "/api/bff/ai/tools/execute",
            json={"tool": "cityos_weather", "params": {"city": "Dakkah"}},
            timeout=10,
        )

    @task(1)
    def execute_traffic_tool(self):
        self.client.post(
            "/api/bff/ai/tools/execute",
            json={"tool": "cityos_traffic", "params": {"zone": "downtown"}},
            timeout=10,
        )
