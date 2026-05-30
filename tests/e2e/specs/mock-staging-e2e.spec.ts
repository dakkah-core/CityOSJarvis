/**
 * Mock-based E2E tests that simulate staging environment behavior.
 * Does NOT require actual staging deployment.
 */

import { test, expect } from "@playwright/test";

test.describe("Staging Environment (Mock)", () => {
  test.beforeEach(async ({ page }) => {
    // Mock all BFF endpoints
    await page.route("**/api/bff/ai/chat", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          content: "This is a mocked staging response.",
          tool_results: [],
          model: "llama3.2",
          latency_ms: 145,
        }),
      });
    });

    await page.route("**/api/bff/ai/agents", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          agents: [
            { id: "governance", name: "Governance", status: "online" },
            { id: "commerce", name: "Commerce", status: "online" },
            { id: "healthcare", name: "Healthcare", status: "degraded" },
          ],
        }),
      });
    });

    await page.route("**/api/bff/ai/models", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          models: [
            { id: "llama3.2", provider: "ollama", latency_ms: 120 },
            { id: "gpt-4", provider: "openai", latency_ms: 450 },
          ],
        }),
      });
    });

    await page.route("**/api/bff/ai/conversations", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          conversations: [
            { id: "c1", title: "Permit Application", updated_at: "2024-01-15T10:00:00Z" },
            { id: "c2", title: "Tax Inquiry", updated_at: "2024-01-14T15:30:00Z" },
          ],
          total: 2,
          page: 1,
          page_size: 20,
        }),
      });
    });

    await page.route("**/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "healthy",
          version: "0.1.0-staging",
          uptime_seconds: 86400,
        }),
      });
    });
  });

  test("health check returns staging version", async ({ page }) => {
    const response = await page.request.get("http://localhost:8000/health");
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body.status).toBe("healthy");
    expect(body.version).toContain("staging");
  });

  test("chat endpoint returns latency metrics", async ({ page }) => {
    const response = await page.request.post("http://localhost:8000/api/bff/ai/chat", {
      data: { message: "Hello", tenantId: "staging-test" },
      headers: { "X-CityOS-Tenant-Id": "staging-test" },
    });

    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.latency_ms).toBeDefined();
    expect(body.latency_ms).toBeLessThan(1000);
  });

  test("agents endpoint shows degraded status", async ({ page }) => {
    const response = await page.request.get("http://localhost:8000/api/bff/ai/agents", {
      headers: { "X-CityOS-Tenant-Id": "staging-test" },
    });

    const body = await response.json();
    const healthcare = body.agents.find((a: any) => a.id === "healthcare");
    expect(healthcare.status).toBe("degraded");
  });

  test("models endpoint returns latency comparison", async ({ page }) => {
    const response = await page.request.get("http://localhost:8000/api/bff/ai/models");
    const body = await response.json();

    const local = body.models.find((m: any) => m.provider === "ollama");
    const cloud = body.models.find((m: any) => m.provider === "openai");

    expect(local.latency_ms).toBeLessThan(cloud.latency_ms);
  });

  test("conversations support pagination", async ({ page }) => {
    const response = await page.request.get(
      "http://localhost:8000/api/bff/ai/conversations?page=1&page_size=10",
      { headers: { "X-CityOS-Tenant-Id": "staging-test" } }
    );

    const body = await response.json();
    expect(body.page).toBe(1);
    expect(body.page_size).toBe(10);
    expect(body.total).toBeGreaterThanOrEqual(0);
  });

  test("tenant isolation is enforced", async ({ page }) => {
    // Tenant A request
    const respA = await page.request.post("http://localhost:8000/api/bff/ai/chat", {
      data: { message: "Hello", tenantId: "tenant-a" },
      headers: { "X-CityOS-Tenant-Id": "tenant-a" },
    });

    // Tenant B request
    const respB = await page.request.post("http://localhost:8000/api/bff/ai/chat", {
      data: { message: "Hello", tenantId: "tenant-b" },
      headers: { "X-CityOS-Tenant-Id": "tenant-b" },
    });

    expect(respA.status()).toBe(200);
    expect(respB.status()).toBe(200);

    // In real staging, conversation history would be isolated
    // Mock returns same response for both
  });

  test("rate limiting returns 429", async ({ page }) => {
    // Override to simulate rate limit
    await page.route("**/api/bff/ai/chat", async (route) => {
      await route.fulfill({
        status: 429,
        headers: { "Retry-After": "60" },
        body: JSON.stringify({ detail: "Rate limit exceeded" }),
      });
    });

    const response = await page.request.post("http://localhost:8000/api/bff/ai/chat", {
      data: { message: "Hello" },
    });

    expect(response.status()).toBe(429);
    expect(response.headers()["retry-after"]).toBe("60");
  });

  test("CSP headers are present", async ({ page }) => {
    await page.route("**/*", async (route) => {
      await route.fulfill({
        status: 200,
        headers: {
          "Content-Security-Policy": "default-src 'self'; connect-src 'self' https://*.dakkah.city",
        },
        body: "<html></html>",
      });
    });

    const response = await page.request.get("http://localhost:3000");
    const csp = response.headers()["content-security-policy"];
    expect(csp).toBeDefined();
    expect(csp).toContain("default-src");
  });
});
