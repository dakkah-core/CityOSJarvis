import { test, expect } from "@playwright/test";

test.describe("Voice E2E", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("voice button triggers recording", async ({ page }) => {
    const voiceButton = page.locator("[data-testid='voice-button']");
    await voiceButton.click();

    await expect(page.locator("[data-testid='voice-orb']")).toHaveAttribute("data-state", "listening");
  });

  test("voice processing shows loading state", async ({ page }) => {
    const voiceButton = page.locator("[data-testid='voice-button']");
    await voiceButton.click();

    // Simulate stop recording
    await voiceButton.click();

    await expect(page.locator("[data-testid='voice-orb']")).toHaveAttribute("data-state", "processing");
  });

  test("TTS audio plays after response", async ({ page }) => {
    // Enable TTS in settings
    await page.click("[data-testid='settings-button']");
    await page.check("[data-testid='tts-toggle']");
    await page.click("[data-testid='close-settings']");

    const voiceButton = page.locator("[data-testid='voice-button']");
    await voiceButton.click();
    await page.waitForTimeout(2000); // Simulate recording
    await voiceButton.click();

    // Wait for audio element to appear
    await page.waitForSelector("audio", { timeout: 15000 });
    const audio = page.locator("audio");
    await expect(audio).toHaveAttribute("src", /data:audio/);
  });

  test("voice error fallback", async ({ page }) => {
    await page.route("**/api/bff/ai/voice/**", (route) => route.abort("internetdisconnected"));

    const voiceButton = page.locator("[data-testid='voice-button']");
    await voiceButton.click();
    await page.waitForTimeout(500);
    await voiceButton.click();

    await expect(page.locator("[data-testid='voice-error']")).toBeVisible();
  });
});
