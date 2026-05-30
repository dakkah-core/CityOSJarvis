"""Locust multi-user simulation for CityOSJarvis staging.

Usage:
    uv run locust -f tests/performance/locustfile.py \
        --host https://staging.dakkah.city \
        --users 100 --spawn-rate 10 --run-time 10m
"""

from __future__ import annotations

import os
import random

from locust import HttpUser, between, task  # type: ignore[import-untyped]


class CityOSJarvisUser(HttpUser):
    """Simulates a citizen using the AI assistant."""

    wait_time = between(1, 5)
    host = os.environ.get("STAGING_URL", "http://localhost:8000")

    def on_start(self) -> None:
        self.tenant_id = f"load-test-{self.user_id}"
        self.api_key = os.environ.get("OPENJARVIS_API_KEY", "")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-CityOS-Tenant-Id": self.tenant_id,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @task(10)
    def chat_message(self) -> None:
        prompts = [
            "What is the weather like?",
            "How do I pay my utility bill?",
            "Explain quantum computing simply.",
            "What are the traffic rules in Dakkah?",
            "How do I apply for a business permit?",
            "Tell me about public transportation.",
            "What hospitals are near me?",
        ]
        prompt = random.choice(prompts)
        with self.client.post(
            "/v1/chat",
            json={"message": prompt, "stream": False},
            headers=self._headers(),
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if data.get("content") or data.get("data"):
                        resp.success()
                    else:
                        resp.failure("Empty response content")
                except Exception:
                    resp.failure("Invalid JSON response")
            elif resp.status_code == 429:
                resp.success()  # Rate limiting is expected under load
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(3)
    def list_agents(self) -> None:
        with self.client.get(
            "/v1/agents",
            headers=self._headers(),
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(2)
    def list_models(self) -> None:
        with self.client.get(
            "/v1/models",
            headers=self._headers(),
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def voice_speak(self) -> None:
        with self.client.post(
            "/v1/voice/speak",
            json={"text": "Welcome to CityOS.", "language": "en"},
            headers=self._headers(),
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 503):
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def health_check(self) -> None:
        with self.client.get("/health", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Health check failed: {resp.status_code}")


class PowerUser(HttpUser):
    """Simulates a government officer with heavy usage patterns."""

    wait_time = between(0.5, 2)
    weight = 1  # 1 power user per 10 regular users

    def on_start(self) -> None:
        self.tenant_id = "government-load-test"
        self.api_key = os.environ.get("OPENJARVIS_API_KEY", "")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-CityOS-Tenant-Id": self.tenant_id,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @task(5)
    def governance_query(self) -> None:
        prompts = [
            "List all pending permits for zone 7",
            "Show compliance violations from last week",
            "Generate safety inspection report",
        ]
        prompt = random.choice(prompts)
        self.client.post(
            "/v1/chat",
            json={"message": prompt, "stream": False},
            headers=self._headers(),
        )

    @task(2)
    def batch_agent_queries(self) -> None:
        for _ in range(5):
            self.client.get("/v1/agents", headers=self._headers())
