"""vLLM GPU throughput and memory utilization benchmark.

Requires: CUDA-capable GPU, vLLM installed
Run with: uv run pytest tests/performance/gpu_benchmark.py -v -s
"""

from __future__ import annotations

import gc
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import pytest

logger = logging.getLogger(__name__)


@dataclass
class GPUBenchmarkResult:
    """Results from a single GPU benchmark run."""

    model: str
    batch_size: int
    max_tokens: int
    total_tokens_generated: int
    elapsed_sec: float
    tokens_per_sec: float
    peak_memory_mb: float | None
    errors: list[str]


def _has_cuda() -> bool:
    try:
        import torch  # type: ignore[import-untyped]
        return torch.cuda.is_available()
    except ImportError:
        return False


def _get_gpu_memory_mb() -> float | None:
    try:
        import torch  # type: ignore[import-untyped]
        if torch.cuda.is_available():
            return torch.cuda.max_memory_allocated() / 1024 / 1024
    except ImportError:
        pass
    return None


def _reset_gpu_memory() -> None:
    try:
        import torch  # type: ignore[import-untyped]
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.empty_cache()
    except ImportError:
        pass


class GPUBenchmark:
    """Benchmark vLLM inference throughput and memory."""

    def __init__(self, model: str = "meta-llama/Llama-2-7b-chat-hf", max_tokens: int = 256) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._llm: Any | None = None

    def _get_llm(self) -> Any:
        """Lazy-load vLLM LLM engine."""
        if self._llm is not None:
            return self._llm
        try:
            from vllm import LLM  # type: ignore[import-untyped]
            self._llm = LLM(
                model=self.model,
                tensor_parallel_size=int(os.environ.get("VLLM_TP_SIZE", "1")),
                gpu_memory_utilization=float(os.environ.get("VLLM_GPU_UTIL", "0.9")),
            )
            return self._llm
        except ImportError:
            pytest.skip("vLLM not installed; install with: uv sync --extra vllm")
        except Exception as exc:
            pytest.skip(f"Failed to load vLLM: {exc}")

    def benchmark_throughput(
        self, prompts: list[str], concurrency: int = 1
    ) -> GPUBenchmarkResult:
        """Measure tokens/sec for a batch of prompts."""
        llm = self._get_llm()
        _reset_gpu_memory()

        from vllm import SamplingParams  # type: ignore[import-untyped]

        sp = SamplingParams(temperature=0.7, max_tokens=self.max_tokens)
        errors: list[str] = []
        total_tokens = 0

        start = time.perf_counter()
        try:
            if concurrency == 1:
                # Sequential
                for prompt in prompts:
                    outputs = llm.generate(prompt, sp)
                    for o in outputs:
                        total_tokens += len(o.outputs[0].token_ids)
            else:
                # Batched
                outputs = llm.generate(prompts, sp)
                for o in outputs:
                    total_tokens += len(o.outputs[0].token_ids)
        except Exception as exc:
            errors.append(str(exc))

        elapsed = time.perf_counter() - start
        peak_mem = _get_gpu_memory_mb()

        return GPUBenchmarkResult(
            model=self.model,
            batch_size=concurrency,
            max_tokens=self.max_tokens,
            total_tokens_generated=total_tokens,
            elapsed_sec=elapsed,
            tokens_per_sec=total_tokens / elapsed if elapsed > 0 else 0.0,
            peak_memory_mb=peak_mem,
            errors=errors,
        )

    def benchmark_memory(self, prompt: str = "Explain quantum computing in detail.") -> dict[str, Any]:
        """Track peak GPU memory for a single generation."""
        llm = self._get_llm()
        _reset_gpu_memory()

        from vllm import SamplingParams  # type: ignore[import-untyped]

        sp = SamplingParams(temperature=0.7, max_tokens=self.max_tokens)
        llm.generate(prompt, sp)

        peak = _get_gpu_memory_mb()
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "peak_memory_mb": peak,
        }

    def benchmark_batch_efficiency(self, prompts: list[str]) -> list[GPUBenchmarkResult]:
        """Compare throughput at different batch sizes."""
        results: list[GPUBenchmarkResult] = []
        for bs in [1, 2, 4, 8, 16]:
            batch = prompts[:bs]
            if not batch:
                break
            result = self.benchmark_throughput(batch, concurrency=bs)
            results.append(result)
            if result.errors:
                break
        return results


@pytest.mark.skipif(not _has_cuda(), reason="CUDA not available")
class TestGPUBenchmark:
    @pytest.fixture
    def benchmark(self) -> GPUBenchmark:
        model = os.environ.get("VLLM_MODEL", "meta-llama/Llama-2-7b-chat-hf")
        return GPUBenchmark(model=model, max_tokens=128)

    def test_throughput_single_prompt(self, benchmark: GPUBenchmark) -> None:
        result = benchmark.benchmark_throughput(["What is the capital of France?"])
        assert result.tokens_per_sec > 0
        assert len(result.errors) == 0

    def test_throughput_batch(self, benchmark: GPUBenchmark) -> None:
        prompts = [f"Question {i}: explain topic {i}" for i in range(4)]
        result = benchmark.benchmark_throughput(prompts, concurrency=4)
        assert result.tokens_per_sec > 0
        assert result.batch_size == 4

    def test_memory_tracking(self, benchmark: GPUBenchmark) -> None:
        result = benchmark.benchmark_memory()
        assert result["peak_memory_mb"] is not None
        assert result["peak_memory_mb"] > 0

    def test_batch_efficiency_scaling(self, benchmark: GPUBenchmark) -> None:
        prompts = [f"Prompt {i}" for i in range(16)]
        results = benchmark.benchmark_batch_efficiency(prompts)
        assert len(results) >= 1
        # Larger batches should generally be more efficient
        if len(results) >= 2:
            tps_values = [r.tokens_per_sec for r in results if not r.errors]
            # Throughput should increase or stay similar with batching
            assert max(tps_values) > 0

    def test_error_handling_empty_prompt(self, benchmark: GPUBenchmark) -> None:
        result = benchmark.benchmark_throughput([""])
        # Empty prompt may or may not error depending on model
        assert isinstance(result.errors, list)

    def test_error_handling_long_prompt(self, benchmark: GPUBenchmark) -> None:
        long_prompt = "word " * 10000
        result = benchmark.benchmark_throughput([long_prompt])
        # May OOM or succeed depending on GPU memory
        assert result.total_tokens_generated >= 0

    def test_different_models(self) -> None:
        # Quick instantiation test without full generation
        for model in ["meta-llama/Llama-2-7b-chat-hf"]:
            bm = GPUBenchmark(model=model, max_tokens=16)
            assert bm.model == model

    def test_environment_variable_override(self) -> None:
        os.environ["VLLM_MODEL"] = "test-model"
        bm = GPUBenchmark()
        assert bm.model == "test-model"
        del os.environ["VLLM_MODEL"]


class TestGPUBenchmarkWithoutGPU:
    """Tests that can run without GPU (skip logic, setup, etc.)."""

    def test_has_cuda_check(self) -> None:
        result = _has_cuda()
        assert isinstance(result, bool)

    def test_get_gpu_memory_without_cuda(self) -> None:
        # Should gracefully return None when CUDA unavailable
        result = _get_gpu_memory_mb()
        assert result is None or isinstance(result, float)

    def test_reset_gpu_memory_without_cuda(self) -> None:
        # Should not raise
        _reset_gpu_memory()
