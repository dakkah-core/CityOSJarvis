/**
 * k6 load test for CityOSJarvis chat endpoint.
 * Run: k6 run tests/performance/k6_chat.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

const chatLatency = new Trend('chat_latency');
const chatErrorRate = new Rate('chat_errors');

export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up
    { duration: '5m', target: 50 },   // Steady state
    { duration: '2m', target: 100 },  // Spike
    { duration: '5m', target: 100 },  // Sustained load
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% under 2s
    http_req_failed: ['rate<0.01'],    // <1% errors
    chat_latency: ['p(95)<3000'],
    chat_errors: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';
const TENANT_ID = __ENV.TENANT_ID || 'perf-test';

const messages = [
  "What's the weather?",
  "How do I pay my bill?",
  "Report a pothole",
  "Book a doctor appointment",
  "Find parking near me",
  "What are today's events?",
  "Check my permit status",
  "Emergency contact numbers",
];

export default function () {
  const payload = JSON.stringify({
    message: messages[Math.floor(Math.random() * messages.length)],
    agentId: 'default',
    stream: false,
  });

  const start = Date.now();
  const res = http.post(`${BASE_URL}/api/bff/ai/chat`, payload, {
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Id': TENANT_ID,
      'X-Correlation-Id': `k6-${__VU}-${__ITER}`,
    },
    timeout: '30s',
  });
  const latency = Date.now() - start;

  chatLatency.add(latency);

  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'response has data': (r) => r.json('success') === true,
    'latency under 3s': () => latency < 3000,
  });

  chatErrorRate.add(!success);

  sleep(Math.random() * 3 + 1);
}
