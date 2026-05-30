"""Mock LLM backend for local benchmark execution.

Simulates a language model API with configurable latency and throughput
for testing benchmarks without requiring a real GPU or cloud service.

Usage:
    uv run python tests/performance/mock_llm_backend.py --port 8080
"""

from __future__ import annotations

import argparse
import json
import random
import time
from http.server import HTTPServer, BaseHTTPRequestHandler


class MockLLMHandler(BaseHTTPRequestHandler):
    """HTTP handler that simulates an LLM API."""

    # Configurable behavior
    min_latency_ms: float = 50.0
    max_latency_ms: float = 500.0
    error_rate: float = 0.0
    stream_chunk_delay_ms: float = 50.0

    def log_message(self, format: str, *args) -> None:
        # Suppress default logging
        pass

    def _send_json(self, status: int, data: dict) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_sse(self, chunks: list[str]) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        for chunk in chunks:
            time.sleep(self.stream_chunk_delay_ms / 1000)
            data = json.dumps({"chunk": chunk})
            self.wfile.write(f"data: {data}\n\n".encode())
            self.wfile.flush()

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "model": "mock-llm"})
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if self.path == "/v1/chat/completions":
            self._handle_chat()
        elif self.path == "/v1/models":
            self._send_json(200, {"data": [{"id": "mock-model"}]})
        else:
            self._send_json(404, {"error": "Not found"})

    def _handle_chat(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()

        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        # Simulate error
        if random.random() < self.error_rate:
            self._send_json(500, {"error": "Internal server error"})
            return

        # Simulate latency
        latency = random.uniform(self.min_latency_ms, self.max_latency_ms)
        time.sleep(latency / 1000)

        stream = request.get("stream", False)
        message = request.get("message", "")

        if stream:
            words = f"This is a mock response to: {message}".split()
            self._send_sse(words)
        else:
            self._send_json(200, {
                "role": "assistant",
                "content": f"This is a mock response to: {message}",
                "usage": {"prompt_tokens": len(message.split()), "completion_tokens": 10},
            })


def run_server(port: int, min_latency: float, max_latency: float, error_rate: float) -> None:
    MockLLMHandler.min_latency_ms = min_latency
    MockLLMHandler.max_latency_ms = max_latency
    MockLLMHandler.error_rate = error_rate

    server = HTTPServer(("", port), MockLLMHandler)
    print(f"Mock LLM server running on http://localhost:{port}")
    print(f"  Latency: {min_latency}-{max_latency}ms")
    print(f"  Error rate: {error_rate * 100:.1f}%")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock LLM Backend")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--min-latency", type=float, default=50.0, help="Minimum latency in ms")
    parser.add_argument("--max-latency", type=float, default=500.0, help="Maximum latency in ms")
    parser.add_argument("--error-rate", type=float, default=0.0, help="Error rate (0-1)")
    args = parser.parse_args()

    run_server(args.port, args.min_latency, args.max_latency, args.error_rate)


if __name__ == "__main__":
    main()
