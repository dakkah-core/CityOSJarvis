/**
 * k6 load test for CityOSJarvis BFF endpoints.
 *
 * Usage:
 *   k6 run --env BASE_URL=https://staging.dakkah.city \
 *          --env API_KEY=$STAGING_API_KEY \
 *          tests/performance/k6-staging.js
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API_KEY = __ENV.API_KEY || "";

// Custom metrics
const chatErrorRate = new Rate("chat_errors");
const voiceErrorRate = new Rate("voice_errors");
const chatLatency = new Trend("chat_latency_ms");
const voiceLatency = new Trend("voice_latency_ms");

export const options = {
  stages: [
    { duration: "2m", target: 10 },   // Ramp up
    { duration: "5m", target: 50 },   // Steady state
    { duration: "2m", target: 100 },  // Stress test
    { duration: "2m", target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<5000"],  // 95% under 5s
    chat_errors: ["rate<0.1"],          // <10% chat errors
    voice_errors: ["rate<0.1"],         // <10% voice errors
  },
};

function getHeaders() {
  const headers = {
    "Content-Type": "application/json",
    "X-CityOS-Tenant-Id": "load-test",
  };
  if (API_KEY) {
    headers["Authorization"] = `Bearer ${API_KEY}`;
  }
  return headers;
}

export function chatLoad() {
  const prompts = [
    "What is the weather like today?",
    "Explain quantum computing simply.",
    "Summarize the theory of relativity.",
    "What are the best practices for API design?",
    "How does photosynthesis work?",
  ];
  const prompt = prompts[Math.floor(Math.random() * prompts.length)];

  const start = Date.now();
  const resp = http.post(
    `${BASE_URL}/v1/chat`,
    JSON.stringify({ message: prompt, stream: false }),
    { headers: getHeaders() }
  );
  const latency = Date.now() - start;
  chatLatency.add(latency);

  const success = check(resp, {
    "chat status is 200": (r) => r.status === 200,
    "chat response has content": (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.content || body.data || body.message;
      } catch {
        return false;
      }
    },
  });

  chatErrorRate.add(!success);
  sleep(Math.random() * 3 + 1); // 1-4s think time
}

export function voiceLoad() {
  const start = Date.now();
  const resp = http.post(
    `${BASE_URL}/v1/voice/speak`,
    JSON.stringify({
      text: "Welcome to Dakkah CityOS. How can I help you today?",
      language: "en",
    }),
    { headers: getHeaders() }
  );
  const latency = Date.now() - start;
  voiceLatency.add(latency);

  const success = check(resp, {
    "voice status is 200 or 503": (r) => r.status === 200 || r.status === 503,
  });

  voiceErrorRate.add(!success);
  sleep(Math.random() * 5 + 2); // 2-7s think time
}

export function agentsList() {
  const resp = http.get(`${BASE_URL}/v1/agents`, { headers: getHeaders() });

  check(resp, {
    "agents status is 200": (r) => r.status === 200,
    "agents returns array": (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.agents || body);
      } catch {
        return false;
      }
    },
  });

  sleep(Math.random() * 2 + 1);
}

export default function () {
  const scenario = Math.random();
  if (scenario < 0.7) {
    chatLoad();
  } else if (scenario < 0.9) {
    agentsList();
  } else {
    voiceLoad();
  }
}
