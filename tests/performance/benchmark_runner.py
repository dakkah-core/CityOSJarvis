"""Performance benchmark runner for CityOSJarvis.

Runs latency, throughput, and memory benchmarks against
a local or remote CityOSJarvis instance.

Usage:
    uv run python tests/performance/benchmark_runner.py --url http://localhost:8000 --duration 60
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx


@dataclass
class BenchmarkResult:
    name: str
    samples: int
    latencies_ms: list[float] = field(default_factory=list)
    errors: int = 0
    timeouts: int = 0

    @property
    def p50(self) -> float:
        return statistics.median(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def p95(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_lat = sorted(self.latencies_ms)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    @property
    def p99(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_lat = sorted(self.latencies_ms)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    @property
    def min_ms(self) -> float:
        return min(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def max_ms(self) -> float:
        return max(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def throughput_rps(self) -> float:
        if not self.latencies_ms:
            return 0.0
        total_sec = sum(self.latencies_ms) / 1000
        return self.samples / total_sec if total_sec > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "samples": self.samples,
            "errors": self.errors,
            "timeouts": self.timeouts,
            "latency_ms": {
                "min": round(self.min_ms, 2),
                "p50": round(self.p50, 2),
                "p95": round(self.p95, 2),
                "p99": round(self.p99, 2),
                "max": round(self.max_ms, 2),
            },
            "throughput_rps": round(self.throughput_rps, 2),
        }


class CityOSJarvisBenchmark:
    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def _post(self, path: str, payload: dict[str, Any], timeout: float = 30.0) -> tuple[float, bool]:
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}{path}",
                    json=payload,
                    headers=self.headers,
                    timeout=timeout,
                )
                latency = (time.perf_counter() - start) * 1000
                return latency, resp.status_code == 200
        except httpx.TimeoutException:
            return (time.perf_counter() - start) * 1000, False
        except Exception:
            return (time.perf_counter() - start) * 1000, False

    async def benchmark_chat(self, samples: int = 50, message: str = "Hello") -> BenchmarkResult:
        result = BenchmarkResult(name="chat_latency", samples=samples)
        for _ in range(samples):
            latency, ok = await self._post(
                "/v1/chat/completions",
                {"message": message, "stream": False},
            )
            if ok:
                result.latencies_ms.append(latency)
            else:
                result.errors += 1
        return result

    async def benchmark_streaming(self, samples: int = 20, message: str = "Tell me a story") -> BenchmarkResult:
        result = BenchmarkResult(name="streaming_latency", samples=samples)
        for _ in range(samples):
            start = time.perf_counter()
            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/v1/chat/completions",
                        json={"message": message, "stream": True},
                        headers=self.headers,
                        timeout=60.0,
                    ) as resp:
                        chunk_count = 0
                        async for _ in resp.aiter_text():
                            chunk_count += 1
                        latency = (time.perf_counter() - start) * 1000
                        if resp.status_code == 200:
                            result.latencies_ms.append(latency)
                        else:
                            result.errors += 1
            except httpx.TimeoutException:
                result.timeouts += 1
            except Exception:
                result.errors += 1
        return result

    async def benchmark_voice_tts(self, samples: int = 20) -> BenchmarkResult:
        result = BenchmarkResult(name="voice_tts_latency", samples=samples)
        for _ in range(samples):
            latency, ok = await self._post(
                "/v1/voice/speak",
                {"text": "Welcome to Dakkah CityOS", "voiceId": "default", "language": "en"},
                timeout=15.0,
            )
            if ok:
                result.latencies_ms.append(latency)
            else:
                result.errors += 1
        return result

    async def benchmark_concurrent_sessions(
        self, concurrency: int = 10, messages_per_session: int = 5
    ) -> BenchmarkResult:
        result = BenchmarkResult(
            name=f"concurrent_{concurrency}x{messages_per_session}",
            samples=concurrency * messages_per_session,
        )

        async def session_worker(session_id: int) -> None:
            for i in range(messages_per_session):
                latency, ok = await self._post(
                    "/v1/chat/completions",
                    {"message": f"Session {session_id} message {i}", "stream": False},
                )
                if ok:
                    result.latencies_ms.append(latency)
                else:
                    result.errors += 1

        await asyncio.gather(*[session_worker(i) for i in range(concurrency)])
        return result


async def main() -> None:
    parser = argparse.ArgumentParser(description="CityOSJarvis Performance Benchmarks")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--api-key", default=None, help="API key")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--output", default="benchmark-results.json", help="Output file")
    args = parser.parse_args()

    benchmark = CityOSJarvisBenchmark(args.url, args.api_key)

    print(f"Starting benchmarks against {args.url}...")
    results: list[BenchmarkResult] = []

    # Chat latency
    print("[1/4] Chat latency benchmark...")
    results.append(await benchmark.benchmark_chat(samples=50))

    # Streaming latency
    print("[2/4] Streaming latency benchmark...")
    results.append(await benchmark.benchmark_streaming(samples=20))

    # Voice TTS latency
    print("[3/4] Voice TTS latency benchmark...")
    results.append(await benchmark.benchmark_voice_tts(samples=20))

    # Concurrent sessions
    print("[4/4] Concurrent sessions benchmark...")
    results.append(await benchmark.benchmark_concurrent_sessions(concurrency=10, messages_per_session=5))

    # Output
    report = {
        "target_url": args.url,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": [r.to_dict() for r in results],
    }

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nResults written to {args.output}")
    for r in results:
        print(f"\n{r.name}:")
        print(f"  Samples: {len(r.latencies_ms)}/{r.samples} (errors: {r.errors}, timeouts: {r.timeouts})")
        print(f"  Latency: p50={r.p50:.1f}ms, p95={r.p95:.1f}ms, p99={r.p99:.1f}ms")
        print(f"  Throughput: {r.throughput_rps:.2f} req/s")


if __name__ == "__main__":
    asyncio.run(main())
