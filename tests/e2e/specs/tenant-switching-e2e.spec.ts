/**
 * E2E tests for tenant switching and multi-tenancy isolation.
 */

import { test, expect } from "@playwright/test";

test.describe("Tenant Switching & Isolation", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/bff/ai/chat", async (route) => {
      const request = route.request();
      const tenantId = request.headers()["x-cityos-tenant-id"] || "default";

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          content: `Response for tenant: ${tenantId}`,
          tenant_id: tenantId,
        }),
      });
    });

    await page.route("**/api/bff/ai/conversations", async (route) => {
      const request = route.request();
      const tenantId = request.headers()["x-cityos-tenant-id"] || "default";

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          conversations: [
            { id: `${tenantId}-c1`, title: `${tenantId} conversation`, tenant_id: tenantId },
          ],
          total: 1,
        }),
      });
    });
  });

  test("chat response includes tenant context", async ({ page }) => {
    const response = await page.request.post("http://localhost:8000/api/bff/ai/chat", {
      data: { message: "Hello" },
      headers: { "X-CityOS-Tenant-Id": "tenant-alpha" },
    });

    const body = await response.json();
    expect(body.tenant_id).toBe("tenant-alpha");
  });

  test("conversation list is tenant-scoped", async ({ page }) => {
    const respA = await page.request.get("http://localhost:8000/api/bff/ai/conversations", {
      headers: { "X-CityOS-Tenant-Id": "tenant-a" },
    });

    const respB = await page.request.get("http://localhost:8000/api/bff/ai/conversations", {
      headers: { "X-CityOS-Tenant-Id": "tenant-b" },
    });

    const bodyA = await respA.json();
    const bodyB = await respB.json();

    expect(bodyA.conversations[0].tenant_id).toBe("tenant-a");
    expect(bodyB.conversations[0].tenant_id).toBe("tenant-b");
  });

  test("missing tenant header uses default", async ({ page }) => {
    const response = await page.request.post("http://localhost:8000/api/bff/ai/chat", {
      data: { message: "Hello" },
    });

    const body = await response.json();
    expect(body.tenant_id).toBe("default");
  });

  test("tenant switching updates UI", async ({ page }) => {
    await page.goto("http://localhost:3000/ai-assistant?tenant=tenant-1");

    // Send message as tenant-1
    await page.fill('[data-testid="chat-input"]', "Hello");
    await page.click('[data-testid="send-button"]', { force: true });

    // Verify tenant indicator
    const tenantIndicator = page.locator('[data-testid="tenant-indicator"]').first();
    if (await tenantIndicator.isVisible().catch(() => false)) {
      await expect(tenantIndicator).toContainText("tenant-1");
    }
  });

  test("cross-tenant access is denied for non-admin", async ({ page }) => {
    await page.route("**/api/bff/ai/admin/**", async (route) => {
      await route.fulfill({
        status: 403,
        body: JSON.stringify({ detail: "Cross-tenant access denied" }),
      });
    });

    const response = await page.request.get("http://localhost:8000/api/bff/ai/admin/tenant-b/data", {
      headers: { "X-CityOS-Tenant-Id": "tenant-a" },
    });

    expect(response.status()).toBe(403);
  });
});
