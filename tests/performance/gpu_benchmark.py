"""GPU benchmark scripts for vLLM inference.

Measures throughput, memory utilization, and batch efficiency.
Requires NVIDIA GPU with CUDA 12.0+.

Usage:
    uv run python tests/performance/gpu_benchmark.py --model meta-llama/Llama-2-7b --max-batch 32
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict, dataclass
from typing import Any


try:
    import torch
    import vllm
    from vllm import LLM, SamplingParams
    HAS_GPU = torch.cuda.is_available()
except ImportError:
    HAS_GPU = False
    torch = None  # type: ignore
    vllm = None  # type: ignore
    LLM = None  # type: ignore
    SamplingParams = None  # type: ignore


@dataclass
class GPUBenchmarkResult:
    name: str
    model: str
    batch_size: int
    throughput_tok_sec: float
    latency_p50_ms: float
    latency_p99_ms: float
    gpu_memory_mb: float
    gpu_utilization_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "batch_size": self.batch_size,
            "throughput_tokens_per_sec": round(self.throughput_tok_sec, 2),
            "latency_ms": {
                "p50": round(self.latency_p50_ms, 2),
                "p99": round(self.latency_p99_ms, 2),
            },
            "gpu": {
                "memory_mb": round(self.gpu_memory_mb, 2),
                "utilization_pct": round(self.gpu_utilization_pct, 2),
            },
        }


def get_gpu_stats() -> tuple[float, float]:
    """Return (memory_used_mb, utilization_pct)."""
    if not HAS_GPU or torch is None:
        return 0.0, 0.0

    memory = torch.cuda.memory_allocated() / 1024 / 1024
    # Utilization requires nvidia-ml-py or pynvml
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        return memory, float(util.gpu)
    except Exception:
        return memory, 0.0


def benchmark_throughput(model: str, batch_sizes: list[int], num_batches: int = 10) -> list[GPUBenchmarkResult]:
    """Benchmark token throughput at various batch sizes."""
    if not HAS_GPU or LLM is None or SamplingParams is None:
        print("WARNING: GPU/vLLM not available, returning mock results")
        return [
            GPUBenchmarkResult(
                name="mock_gpu_benchmark",
                model=model,
                batch_size=bs,
                throughput_tok_sec=bs * 50.0,
                latency_p50_ms=1000.0 / bs,
                latency_p99_ms=2000.0 / bs,
                gpu_memory_mb=4096.0 + bs * 128,
                gpu_utilization_pct=80.0,
            )
            for bs in batch_sizes
        ]

    llm = LLM(model=model, tensor_parallel_size=1)
    sampling_params = SamplingParams(temperature=0.7, max_tokens=256)
    prompt = "Explain quantum computing in simple terms:"

    results: list[GPUBenchmarkResult] = []

    for batch_size in batch_sizes:
        prompts = [prompt] * batch_size
        latencies: list[float] = []

        # Warmup
        llm.generate(prompts[:1], sampling_params)

        for _ in range(num_batches):
            start = time.perf_counter()
            outputs = llm.generate(prompts, sampling_params)
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)

            total_tokens = sum(len(o.outputs[0].token_ids) for o in outputs)
            throughput = total_tokens / (latency / 1000)

        memory, util = get_gpu_stats()

        results.append(GPUBenchmarkResult(
            name=f"batch_{batch_size}",
            model=model,
            batch_size=batch_size,
            throughput_tok_sec=throughput,
            latency_p50_ms=statistics.median(latencies),
            latency_p99_ms=sorted(latencies)[int(len(latencies) * 0.99)],
            gpu_memory_mb=memory,
            gpu_utilization_pct=util,
        ))

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="GPU Benchmark for CityOSJarvis")
    parser.add_argument("--model", default="meta-llama/Llama-2-7b-hf", help="Model name")
    parser.add_argument("--batch-sizes", default="1,4,8,16,32", help="Comma-separated batch sizes")
    parser.add_argument("--num-batches", type=int, default=10, help="Number of batches per size")
    parser.add_argument("--output", default="gpu-benchmark-results.json", help="Output file")
    args = parser.parse_args()

    batch_sizes = [int(x) for x in args.batch_sizes.split(",")]

    print(f"GPU available: {HAS_GPU}")
    print(f"Model: {args.model}")
    print(f"Batch sizes: {batch_sizes}")

    results = benchmark_throughput(args.model, batch_sizes, args.num_batches)

    report = {
        "model": args.model,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gpu_available": HAS_GPU,
        "results": [r.to_dict() for r in results],
    }

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nResults written to {args.output}")
    for r in results:
        print(f"\nBatch {r.batch_size}:")
        print(f"  Throughput: {r.throughput_tok_sec:.1f} tok/s")
        print(f"  Latency: p50={r.latency_p50_ms:.1f}ms, p99={r.latency_p99_ms:.1f}ms")
        print(f"  GPU: {r.gpu_memory_mb:.0f}MB, {r.gpu_utilization_pct:.1f}%")


if __name__ == "__main__":
    main()
