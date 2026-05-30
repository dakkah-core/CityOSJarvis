import { test, expect } from "@playwright/test";

/**
 * Health check E2E tests for the AI infrastructure stack.
 *
 * Prerequisites:
 *   docker compose -f deploy/docker/docker-compose.build.yml up -d
 */

const JARVIS_URL = process.env.E2E_JARVIS_URL || "http://localhost:8000";
const LITELLM_URL = process.env.E2E_LITELLM_URL || "http://localhost:4000";
const OLLAMA_URL = process.env.E2E_OLLAMA_URL || "http://localhost:11434";

test.describe("AI Stack Health Checks", () => {
  test("CityOSJarvis health endpoint returns 200", async ({ request }) => {
    const res = await request.get(`${JARVIS_URL}/health`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("status", "ok");
  });

  test("LiteLLM proxy health endpoint returns 200", async ({ request }) => {
    const res = await request.get(`${LITELLM_URL}/health/liveliness`);
    expect(res.status()).toBe(200);
  });

  test("LiteLLM proxy lists configured models", async ({ request }) => {
    const res = await request.get(`${LITELLM_URL}/v1/models`, {
      headers: {
        Authorization: `Bearer ${process.env.LITELLM_MASTER_KEY || "sk-litellm-cityos-local"}`,
      },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.data).toBeInstanceOf(Array);
    expect(body.data.length).toBeGreaterThan(0);

    const modelIds = body.data.map((m: any) => m.id);
    // Verify all configured providers are present
    expect(modelIds).toContain("gpt-4o");
    expect(modelIds).toContain("gpt-4o-mini");
    expect(modelIds).toContain("claude-sonnet-4");
    expect(modelIds).toContain("gemini-pro");
    expect(modelIds).toContain("kimi-k2");
    expect(modelIds).toContain("llama-local");
  });

  test("Ollama health endpoint returns 200", async ({ request }) => {
    const res = await request.get(`${OLLAMA_URL}/api/tags`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("models");
  });
});
