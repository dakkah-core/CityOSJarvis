import { test, expect } from "@playwright/test";
import { createStandardMockServer } from "../fixtures/mock-server";

/**
 * E2E tests using mock server — no external dependencies required.
 * These tests validate UI behavior without needing staging environment.
 */

test.describe("Mock E2E (No External Dependencies)", () => {
  const mockServer = createStandardMockServer(9998);

  test.beforeAll(async () => {
    await mockServer.start();
  });

  test.afterAll(async () => {
    await mockServer.stop();
  });

  test.beforeEach(async ({ page }) => {
    // Override API calls to use mock server
    await page.route("**/api/bff/ai/**", (route) => {
      const url = new URL(route.request().url());
      const mockUrl = `http://localhost:9998${url.pathname}`;
      route.continue({ url: mockUrl });
    });

    await page.goto("/");
    await page.waitForSelector("[data-testid='chat-input']", { timeout: 10000 });
  });

  test("chat flow with mock server", async ({ page }) => {
    const input = page.locator("[data-testid='chat-input']");
    await input.fill("What services are available?");
    await page.keyboard.press("Enter");

    await page.waitForSelector("[data-testid='message-bubble-assistant']", { timeout: 10000 });
    const response = page.locator("[data-testid='message-bubble-assistant']").last();
    await expect(response).toContainText("Dakkah CityOS");
  });

  test("agent list loads from mock", async ({ page }) => {
    await page.click("[data-testid='agent-selector-trigger']");
    await expect(page.locator("[data-testid='agent-item']")).toHaveCount(3);
  });

  test("model list loads from mock", async ({ page }) => {
    await page.click("[data-testid='model-selector-trigger']");
    await expect(page.locator("[data-testid='model-item']")).toHaveCount(2);
  });

  test("voice synthesis returns mock audio", async ({ page }) => {
    await page.click("[data-testid='settings-button']");
    await page.check("[data-testid='tts-toggle']");
    await page.click("[data-testid='close-settings']");

    const voiceButton = page.locator("[data-testid='voice-button']");
    await voiceButton.click();
    await page.waitForTimeout(500);
    await voiceButton.click();

    await page.waitForSelector("audio", { timeout: 10000 });
  });

  test("tool execution returns mock result", async ({ page }) => {
    const input = page.locator("[data-testid='chat-input']");
    await input.fill("/tool cityos_weather city=Dakkah");
    await page.keyboard.press("Enter");

    await page.waitForSelector("[data-testid='tool-result']", { timeout: 10000 });
    await expect(page.locator("[data-testid='tool-result']")).toContainText("successfully");
  });

  test("health check shows green status", async ({ page }) => {
    await page.click("[data-testid='status-indicator']");
    await expect(page.locator("[data-testid='status-tooltip']")).toContainText("ok");
  });

  test("offline mode shows cached agents", async ({ page }) => {
    // Simulate offline
    await page.context().setOffline(true);

    await page.reload();
    await page.waitForSelector("[data-testid='chat-input']", { timeout: 5000 });

    // Should still show cached agent list
    await page.click("[data-testid='agent-selector-trigger']");
    await expect(page.locator("[data-testid='agent-item']")).toHaveCount(3);

    await page.context().setOffline(false);
  });
});
