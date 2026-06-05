"""Unit tests for the benchmark runner utilities."""

from __future__ import annotations

import pytest
from benchmark_runner import BenchmarkResult, CityOSJarvisBenchmark


class TestBenchmarkResult:
    def test_empty_result(self) -> None:
        r = BenchmarkResult(name="test", samples=0)
        assert r.p50 == 0.0
        assert r.p95 == 0.0
        assert r.p99 == 0.0
        assert r.throughput_rps == 0.0

    def test_percentiles(self) -> None:
        r = BenchmarkResult(name="test", samples=100)
        r.latencies_ms = list(range(1, 101))  # 1..100
        assert r.p50 == 50.5
        # p95 index = int(100 * 0.95) = 95, element at index 95 is 96
        assert r.p95 == 96
        # p99 index = int(100 * 0.99) = 99, element at index 99 is 100
        assert r.p99 == 100

    def test_percentiles_with_duplicates(self) -> None:
        r = BenchmarkResult(name="test", samples=10)
        r.latencies_ms = [10.0] * 10
        assert r.p50 == 10.0
        assert r.p95 == 10.0

    def test_throughput_calculation(self) -> None:
        r = BenchmarkResult(name="test", samples=2)
        r.latencies_ms = [100.0, 200.0]  # 300ms total = 0.3s
        # 2 requests / 0.3s = ~6.67 rps
        assert r.throughput_rps == pytest.approx(6.67, rel=0.01)

    def test_to_dict_structure(self) -> None:
        r = BenchmarkResult(name="chat", samples=10, errors=1, timeouts=0)
        r.latencies_ms = [10.0, 20.0, 30.0]
        d = r.to_dict()
        assert d["name"] == "chat"
        assert d["samples"] == 10
        assert d["errors"] == 1
        assert "latency_ms" in d
        assert "throughput_rps" in d


class TestCityOSJarvisBenchmark:
    def test_init_with_api_key(self) -> None:
        b = CityOSJarvisBenchmark("http://localhost:8000", api_key="secret")
        assert b.headers["Authorization"] == "Bearer secret"

    def test_init_without_api_key(self) -> None:
        b = CityOSJarvisBenchmark("http://localhost:8000")
        assert "Authorization" not in b.headers

    def test_base_url_stripped(self) -> None:
        b = CityOSJarvisBenchmark("http://localhost:8000/")
        assert b.base_url == "http://localhost:8000"
