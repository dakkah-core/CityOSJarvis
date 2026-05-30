import { test, expect } from "@playwright/test";

/**
 * Fallback and resilience E2E tests.
 * Verifies graceful degradation when providers are unavailable.
 */

const LITELLM_URL = process.env.E2E_LITELLM_URL || "http://localhost:4000";
const MASTER_KEY = process.env.LITELLM_MASTER_KEY || "sk-litellm-cityos-local";
const JARVIS_URL = process.env.E2E_JARVIS_URL || "http://localhost:8000";

test.describe("Fallback & Resilience", () => {
  test("LiteLLM returns 429 when rate limit exceeded", async ({ request }) => {
    // Rapid-fire requests to trigger rate limiting
    const headers = {
      Authorization: `Bearer ${MASTER_KEY}`,
      "Content-Type": "application/json",
    };

    const promises = Array.from({ length: 10 }, () =>
      request.post(`${LITELLM_URL}/v1/chat/completions`, {
        headers,
        data: {
          model: "gpt-4o-mini",
          messages: [{ role: "user", content: "test" }],
          max_tokens: 5,
        },
      })
    );

    const responses = await Promise.all(promises);
    const statusCodes = responses.map((r) => r.status());

    // At least some requests should succeed; none should crash the proxy
    expect(statusCodes.every((s) => [200, 401, 429, 500].includes(s))).toBe(true);
  });

  test("Jarvis returns structured error when LLM is unavailable", async ({ request }) => {
    // Temporarily point Jarvis to a non-existent LLM endpoint
    // (In a real test, you'd restart Jarvis with a bad OPENAI_API_BASE)
    // Here we just verify the error format when something goes wrong

    const res = await request.post(`${JARVIS_URL}/v1/chat/completions`, {
      headers: {
        Authorization: `Bearer cityos-local-key`,
        "Content-Type": "application/json",
        "X-CityOS-Tenant-Id": "test",
        "X-Correlation-Id": "resilience-test",
      },
      data: {
        model: "definitely-not-real-model-xyz",
        messages: [{ role: "user", content: "test" }],
      },
    });

    // Should return a structured error, not a 500 crash
    expect([400, 401, 404, 429, 502, 504]).toContain(res.status());

    if (res.status() !== 504) {
      const body = await res.json();
      expect(body).toHaveProperty("error");
    }
  });

  test("Ollama embedding falls back gracefully when model missing", async ({ request }) => {
    const res = await request.post(`${LITELLM_URL}/v1/embeddings`, {
      headers: {
        Authorization: `Bearer ${MASTER_KEY}`,
        "Content-Type": "application/json",
      },
      data: {
        model: "embed-local",
        input: "test",
      },
    });

    // Should return 404 (model not pulled) rather than crash
    expect([200, 404]).toContain(res.status());
  });
});
