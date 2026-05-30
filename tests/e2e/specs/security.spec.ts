import { test, expect } from "@playwright/test";

test.describe("Security E2E", () => {
  test("unauthenticated request redirects to login", async ({ page }) => {
    // Clear any existing auth
    await page.context().clearCookies();
    await page.goto("/");

    // Should redirect to Keycloak or show login prompt
    await expect(page).toHaveURL(/login|auth/);
  });

  test("PHI in query gets blocked", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("[data-testid='chat-input']");

    const input = page.locator("[data-testid='chat-input']");
    await input.fill("My national ID is 1234567890");
    await page.keyboard.press("Enter");

    await expect(page.locator("[data-testid='compliance-blocked']")).toBeVisible();
    await expect(page.locator("[data-testid='compliance-blocked']")).toContainText(/sensitive|blocked/i);
  });

  test("credit card in query gets blocked", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("[data-testid='chat-input']");

    const input = page.locator("[data-testid='chat-input']");
    await input.fill("My card is 4111 1111 1111 1111");
    await page.keyboard.press("Enter");

    await expect(page.locator("[data-testid='compliance-blocked']")).toBeVisible();
  });

  test("cross-tenant access denied", async ({ page, context }) => {
    // Set auth for tenant A
    await context.addCookies([
      { name: "tenant_id", value: "tenant-a", domain: "localhost", path: "/" },
    ]);

    await page.goto("/?tenant=tenant-b");
    await expect(page.locator("[data-testid='access-denied']")).toBeVisible();
  });

  test("rate limit after excessive requests", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("[data-testid='chat-input']");

    const input = page.locator("[data-testid='chat-input']");

    // Send many rapid requests
    for (let i = 0; i < 15; i++) {
      await input.fill(`Message ${i}`);
      await page.keyboard.press("Enter");
      await page.waitForTimeout(100);
    }

    // Should eventually see rate limit
    await expect(page.locator("[data-testid='rate-limit-message']")).toBeVisible();
  });

  test("CSP headers prevent XSS", async ({ page }) => {
    await page.goto("/");
    const response = await page.waitForResponse((resp) => resp.url() === page.url());
    const csp = await response.headerValue("content-security-policy");
    expect(csp).toBeTruthy();
    expect(csp).toContain("default-src");
  });
});
