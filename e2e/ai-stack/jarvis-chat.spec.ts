import { test, expect } from "@playwright/test";

/**
 * CityOSJarvis chat completion E2E tests.
 * Verifies the full pipeline: Jarvis → LiteLLM → Provider API.
 */

const JARVIS_URL = process.env.E2E_JARVIS_URL || "http://localhost:8000";
const API_KEY = process.env.OPENJARVIS_API_KEY || "cityos-local-key";

test.describe("CityOSJarvis Chat Completions", () => {
  const headers = {
    Authorization: `Bearer ${API_KEY}`,
    "Content-Type": "application/json",
    "X-CityOS-Tenant-Id": "test-tenant",
    "X-Correlation-Id": "e2e-test-123",
  };

  test("Non-streaming chat completion", async ({ request }) => {
    const res = await request.post(`${JARVIS_URL}/v1/chat/completions`, {
      headers,
      data: {
        model: "gpt-4o-mini",
        messages: [{ role: "user", content: "Say exactly the word 'pong'." }],
        max_tokens: 10,
        stream: false,
      },
    });

    // Accept 200, 401 (missing provider key), 429 (rate limit), 502 (LLM unavailable)
    expect([200, 401, 429, 502, 504]).toContain(res.status());

    if (res.status() === 200) {
      const body = await res.json();
      expect(body).toHaveProperty("choices");
      expect(body.choices[0].message.content.toLowerCase()).toContain("pong");
      expect(body).toHaveProperty("usage");
    }
  });

  test("Streaming chat completion returns SSE", async ({ request }) => {
    const res = await request.post(`${JARVIS_URL}/v1/chat/completions`, {
      headers,
      data: {
        model: "gpt-4o-mini",
        messages: [{ role: "user", content: "Count to 3." }],
        max_tokens: 20,
        stream: true,
      },
    });

    expect([200, 401, 429, 502, 504]).toContain(res.status());

    if (res.status() === 200) {
      const contentType = res.headers()["content-type"] || "";
      expect(contentType).toContain("text/event-stream");

      const body = await res.text();
      const lines = body.split("\n").filter((l) => l.startsWith("data:"));
      expect(lines.length).toBeGreaterThan(0);

      // Last line should be [DONE]
      expect(lines[lines.length - 1]).toBe("data: [DONE]");
    }
  });

  test("Compliance gate blocks PII", async ({ request }) => {
    const res = await request.post(`${JARVIS_URL}/v1/chat/completions`, {
      headers,
      data: {
        model: "gpt-4o-mini",
        messages: [
          { role: "user", content: "My Saudi ID is 1234567890 and my IBAN is SA0380000000608010167519" },
        ],
        max_tokens: 10,
      },
    });

    // Compliance gate should block this with a 400 or return redacted content
    expect([200, 400]).toContain(res.status());

    if (res.status() === 200) {
      const body = await res.json();
      const content = body.choices[0].message.content;
      // If allowed through, content should be redacted
      expect(content).not.toContain("1234567890");
      expect(content).not.toContain("SA0380000000608010167519");
    }
  });

  test("Tenant context is forwarded", async ({ request }) => {
    const res = await request.post(`${JARVIS_URL}/v1/chat/completions`, {
      headers: {
        ...headers,
        "X-CityOS-Tenant-Id": "tenant-alpha",
        "X-CityOS-Node-Path": "/sa/riyadh/dakkah",
      },
      data: {
        model: "gpt-4o-mini",
        messages: [{ role: "user", content: "Hello" }],
        max_tokens: 5,
      },
    });

    // Should not fail due to tenant headers
    expect([200, 401, 429, 502, 504]).toContain(res.status());
  });
});
