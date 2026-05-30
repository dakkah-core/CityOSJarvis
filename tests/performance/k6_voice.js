/**
 * k6 load test for CityOSJarvis voice endpoints.
 * Run: k6 run tests/performance/k6_voice.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

const ttsLatency = new Trend('tts_latency');
const ttsErrorRate = new Rate('tts_errors');

export const options = {
  stages: [
    { duration: '1m', target: 20 },
    { duration: '3m', target: 20 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.02'],
    tts_latency: ['p(95)<8000'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';
const TENANT_ID = __ENV.TENANT_ID || 'perf-test';

export default function () {
  // TTS synthesis
  const payload = JSON.stringify({
    text: 'Welcome to Dakkah CityOS. How can I help you today?',
    voiceId: 'default',
    language: 'en',
  });

  const start = Date.now();
  const res = http.post(`${BASE_URL}/api/bff/ai/voice/speak`, payload, {
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Id': TENANT_ID,
    },
    timeout: '15s',
  });
  const latency = Date.now() - start;

  ttsLatency.add(latency);

  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'has audioBase64': (r) => r.json('audioBase64') !== undefined,
  });

  ttsErrorRate.add(!success);

  sleep(Math.random() * 5 + 2);
}
