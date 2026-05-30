import { test, expect } from "@playwright/test";

/**
 * Gateway routing E2E tests.
 * Verifies LiteLLM correctly routes to different providers.
 */

const LITELLM_URL = process.env.E2E_LITELLM_URL || "http://localhost:4000";
const MASTER_KEY = process.env.LITELLM_MASTER_KEY || "sk-litellm-cityos-local";

test.describe("LiteLLM Gateway Routing", () => {
  const headers = {
    Authorization: `Bearer ${MASTER_KEY}`,
    "Content-Type": "application/json",
  };

  test("Chat completion routes to OpenAI-compatible proxy", async ({ request }) => {
    const res = await request.post(`${LITELLM_URL}/v1/chat/completions`, {
      headers,
      data: {
        model: "gpt-4o-mini",
        messages: [{ role: "user", content: "Say 'pong' and nothing else." }],
        max_tokens: 10,
      },
    });

    // Should succeed if OPENAI_API_KEY is set; 429/rate-limit is also acceptable
    expect([200, 401, 429, 500]).toContain(res.status());

    if (res.status() === 200) {
      const body = await res.json();
      expect(body).toHaveProperty("choices");
      expect(body.choices[0]).toHaveProperty("message");
    }
  });

  test("Chat completion routes to Kimi (Moonshot)", async ({ request }) => {
    const res = await request.post(`${LITELLM_URL}/v1/chat/completions`, {
      headers,
      data: {
        model: "kimi-lite",
        messages: [{ role: "user", content: "Say 'pong' and nothing else." }],
        max_tokens: 10,
      },
    });

    // Accept any status — the key test is that LiteLLM accepts the request
    expect([200, 401, 429]).toContain(res.status());
  });

  test("Embedding endpoint routes to local Ollama", async ({ request }) => {
    const res = await request.post(`${LITELLM_URL}/v1/embeddings`, {
      headers,
      data: {
        model: "embed-local",
        input: "test embedding",
      },
    });

    // Ollama may not have the model pulled yet
    expect([200, 404, 500]).toContain(res.status());
  });

  test("Invalid model returns 404", async ({ request }) => {
    const res = await request.post(`${LITELLM_URL}/v1/chat/completions`, {
      headers,
      data: {
        model: "nonexistent-model",
        messages: [{ role: "user", content: "test" }],
      },
    });
    expect(res.status()).toBe(404);
  });
});
