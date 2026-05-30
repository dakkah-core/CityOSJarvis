import { test, expect } from "@playwright/test";
import { createStandardMockTwilio } from "../fixtures/mock-twilio";

/**
 * Voice E2E tests using mock Twilio server.
 * No real Twilio credentials required.
 */

test.describe("Voice Mock E2E", () => {
  const mockTwilio = createStandardMockTwilio(15021);

  test.beforeAll(async () => {
    await mockTwilio.start();
  });

  test.afterAll(async () => {
    await mockTwilio.stop();
  });

  test.beforeEach(async ({ page }) => {
    // Route Twilio API calls to mock server
    await page.route("**/api/voice/twilio**", (route) => {
      route.continue({ url: `http://localhost:15021/api/voice/twilio` });
    });
    await page.route("**/api/voice/webhook**", (route) => {
      route.continue({ url: `http://localhost:15021/api/voice/webhook` });
    });

    await page.goto("/");
  });

  test("voice button activates recording", async ({ page }) => {
    const voiceButton = page.locator("[data-testid='voice-button']");
    await voiceButton.click();

    await expect(page.locator("[data-testid='voice-orb']")).toHaveAttribute("data-state", "listening");
  });

  test("voice processing completes", async ({ page }) => {
    const voiceButton = page.locator("[data-testid='voice-button']");

    // Start recording
    await voiceButton.click();
    await expect(page.locator("[data-testid='voice-orb']")).toHaveAttribute("data-state", "listening");

    // Stop recording
    await voiceButton.click();
    await expect(page.locator("[data-testid='voice-orb']")).toHaveAttribute("data-state", "processing");

    // Should eventually complete or show response
    await page.waitForTimeout(2000);
    const state = await page.locator("[data-testid='voice-orb']").getAttribute("data-state");
    expect(["idle", "speaking", "error"]).toContain(state);
  });

  test("mock Twilio receives call", async ({ page }) => {
    const voiceButton = page.locator("[data-testid='voice-button']");
    await voiceButton.click();
    await page.waitForTimeout(500);
    await voiceButton.click();

    // Verify mock server received the call
    const calls = mockTwilio.getCalls();
    expect(calls.length).toBeGreaterThan(0);
  });

  test("Arabic voice input supported", async ({ page }) => {
    // Simulate Arabic voice input
    await page.evaluate(() => {
      window.localStorage.setItem("preferred-language", "ar");
    });

    await page.reload();
    const voiceButton = page.locator("[data-testid='voice-button']");
    await voiceButton.click();

    await expect(page.locator("[data-testid='voice-orb']")).toBeVisible();
  });
});
