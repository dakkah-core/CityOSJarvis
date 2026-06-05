"""Cloud LLM latency benchmark — Ollama local vs cloud fallback vs BFF proxy overhead.

Usage:
    uv run python tests/performance/cloud_latency_benchmark.py \
        --base-url http://localhost:8000 \
        --api-key $OPENJARVIS_API_KEY \
        --iterations 50
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from dataclasses import asdict, dataclass
from typing import Any

import httpx


@dataclass
class LatencyResult:
    backend: str
    prompt: str
    latency_ms: float
    tokens_generated: int
    timestamp: str


class CloudLatencyBenchmark:
    """Benchmark latency across local Ollama, cloud fallback, and BFF proxy."""

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=120.0)

    async def __aenter__(self) -> CloudLatencyBenchmark:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.client.aclose()

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def benchmark_local_ollama(
        self, prompt: str, model: str = "llama3.2"
    ) -> LatencyResult | None:
        """Measure latency against local Ollama backend."""
        ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        start = time.perf_counter()
        try:
            resp = await self.client.post(
                f"{ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
            elapsed_ms = (time.perf_counter() - start) * 1000
            return LatencyResult(
                backend="ollama-local",
                prompt=prompt[:50],
                latency_ms=round(elapsed_ms, 2),
                tokens_generated=data.get("eval_count", 0),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        except Exception as exc:
            print(f"Ollama benchmark failed: {exc}")
            return None

    async def benchmark_bff_chat(
        self, prompt: str, tenant_id: str = "benchmark"
    ) -> LatencyResult | None:
        """Measure latency through CityOSJarvis BFF chat endpoint."""
        start = time.perf_counter()
        try:
            resp = await self.client.post(
                f"{self.base_url}/v1/chat",
                headers={**self._headers(), "X-CityOS-Tenant-Id": tenant_id},
                json={"message": prompt, "stream": False},
            )
            resp.raise_for_status()
            elapsed_ms = (time.perf_counter() - start) * 1000
            return LatencyResult(
                backend="cityosjarvis-bff",
                prompt=prompt[:50],
                latency_ms=round(elapsed_ms, 2),
                tokens_generated=0,  # Not exposed in simple chat response
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        except Exception as exc:
            print(f"BFF benchmark failed: {exc}")
            return None

    async def benchmark_streaming_latency(
        self, prompt: str, tenant_id: str = "benchmark"
    ) -> LatencyResult | None:
        """Measure time-to-first-chunk for streaming responses."""
        start = time.perf_counter()
        first_chunk_time: float | None = None
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/v1/chat",
                headers={**self._headers(), "X-CityOS-Tenant-Id": tenant_id},
                json={"message": prompt, "stream": True},
            ) as resp:
                resp.raise_for_status()
                async for _ in resp.aiter_text():
                    if first_chunk_time is None:
                        first_chunk_time = time.perf_counter()
                    break  # Only measure time-to-first-chunk

            ttfb_ms = (first_chunk_time - start) * 1000 if first_chunk_time else 0
            return LatencyResult(
                backend="streaming-ttfb",
                prompt=prompt[:50],
                latency_ms=round(ttfb_ms, 2),
                tokens_generated=0,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        except Exception as exc:
            print(f"Streaming benchmark failed: {exc}")
            return None

    @staticmethod
    def summarize(results: list[LatencyResult]) -> dict[str, Any]:
        """Compute p50/p95/p99 from a list of results."""
        if not results:
            return {}
        latencies = [r.latency_ms for r in results]
        latencies.sort()
        n = len(latencies)
        return {
            "backend": results[0].backend,
            "samples": n,
            "p50_ms": round(statistics.median(latencies), 2),
            "p95_ms": round(latencies[int(n * 0.95)], 2),
            "p99_ms": round(latencies[int(n * 0.99)], 2),
            "min_ms": round(latencies[0], 2),
            "max_ms": round(latencies[-1], 2),
            "mean_ms": round(statistics.mean(latencies), 2),
            "stddev_ms": round(statistics.stdev(latencies), 2) if n > 1 else 0.0,
        }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Cloud LLM latency benchmark")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--api-key", default=os.environ.get("OPENJARVIS_API_KEY"))
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument(
        "--prompt", default="Explain the theory of relativity in simple terms."
    )
    parser.add_argument("--output", default=".build/reports/cloud_latency.json")
    args = parser.parse_args()

    prompts = [
        args.prompt,
        "Summarize the key points of machine learning.",
        "What are the benefits of renewable energy?",
        "Describe the process of photosynthesis.",
        "How does blockchain technology work?",
    ]

    async with CloudLatencyBenchmark(args.base_url, args.api_key) as bm:
        all_results: list[LatencyResult] = []

        for backend_name, bench_fn in [
            ("ollama-local", bm.benchmark_local_ollama),
            ("cityosjarvis-bff", bm.benchmark_bff_chat),
            ("streaming-ttfb", bm.benchmark_streaming_latency),
        ]:
            backend_results: list[LatencyResult] = []
            for i in range(args.iterations):
                prompt = prompts[i % len(prompts)]
                result = await bench_fn(prompt)
                if result:
                    backend_results.append(result)
                    all_results.append(result)
                await asyncio.sleep(0.5)  # Rate limit protection

            summary = CloudLatencyBenchmark.summarize(backend_results)
            print(f"\n{backend_name}:")
            print(json.dumps(summary, indent=2))

        # Write full report
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(
                {
                    "results": [asdict(r) for r in all_results],
                    "summaries": {
                        "ollama": CloudLatencyBenchmark.summarize(
                            [r for r in all_results if r.backend == "ollama-local"]
                        ),
                        "bff": CloudLatencyBenchmark.summarize(
                            [r for r in all_results if r.backend == "cityosjarvis-bff"]
                        ),
                        "streaming": CloudLatencyBenchmark.summarize(
                            [r for r in all_results if r.backend == "streaming-ttfb"]
                        ),
                    },
                },
                f,
                indent=2,
            )
        print(f"\nReport written to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
