# CityOSJarvis Performance Testing

## Benchmarks

### GPU Benchmark (`gpu_benchmark.py`)
Requires: CUDA-capable GPU, vLLM installed

```bash
# Install vLLM extra
uv sync --extra vllm

# Run all GPU benchmarks
uv run pytest tests/performance/gpu_benchmark.py -v -s

# Set model via environment
VLLM_MODEL=meta-llama/Llama-2-7b-chat-hf uv run pytest tests/performance/gpu_benchmark.py
```

Metrics collected:
- **Throughput**: tokens/sec at various batch sizes (1, 2, 4, 8, 16)
- **Memory**: Peak GPU memory utilization per generation
- **Efficiency**: Batch scaling efficiency curve

Skipped automatically when CUDA is unavailable.

### Cloud Latency Benchmark (`cloud_latency_benchmark.py`)
Requires: Running CityOSJarvis backend (local or staging)

```bash
# Local backend
uv run python tests/performance/cloud_latency_benchmark.py --base-url http://localhost:8000

# Staging
uv run python tests/performance/cloud_latency_benchmark.py \
  --base-url https://staging.dakkah.city \
  --api-key $STAGING_API_KEY \
  --iterations 50
```

Compares:
- **Ollama local** direct latency
- **BFF proxy** overhead
- **Streaming TTFB** (time-to-first-chunk)

Outputs `.build/reports/cloud_latency.json` with p50/p95/p99 summaries.

## Load Tests

### k6 (`k6-staging.js`)
Requires: [k6](https://k6.io/) installed

```bash
k6 run --env BASE_URL=https://staging.dakkah.city \
       --env API_KEY=$STAGING_API_KEY \
       tests/performance/k6-staging.js
```

Stages: 2m ramp → 5m steady (50 RPS) → 2m stress (100 RPS) → 2m ramp-down

### Locust (`locustfile.py`)
Requires: `uv sync --extra locust` or `pip install locust`

```bash
uv run locust -f tests/performance/locustfile.py \
  --host https://staging.dakkah.city \
  --users 100 --spawn-rate 10 --run-time 10m
```

User classes:
- `CityOSJarvisUser` (weight 10): Citizen chat/agent/voice patterns
- `PowerUser` (weight 1): Government officer heavy governance queries
