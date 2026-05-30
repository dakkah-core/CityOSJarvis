import { test, expect } from "@playwright/test";
import stagingConfig from "../staging.config";

test.describe("Chat E2E", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("[data-testid='chat-input']", { timeout: 10000 });
  });

  test("send message and receive response", async ({ page }) => {
    const input = page.locator("[data-testid='chat-input']");
    await input.fill("What services does Dakkah CityOS offer?");
    await page.keyboard.press("Enter");

    // Wait for response
    await page.waitForSelector("[data-testid='message-bubble-assistant']", { timeout: 30000 });
    const response = page.locator("[data-testid='message-bubble-assistant']").last();
    await expect(response).toContainText(/Dakkah|CityOS|service/i);
  });

  test("switch agent mid-conversation", async ({ page }) => {
    await page.click("[data-testid='agent-selector-trigger']");
    await page.click("[data-testid='agent-merchant']");
    await expect(page.locator("[data-testid='active-agent-name']")).toContainText("Merchant");
  });

  test("streaming response shows typing indicator", async ({ page }) => {
    const input = page.locator("[data-testid='chat-input']");
    await input.fill("Tell me a long story");
    await page.keyboard.press("Enter");

    // Typing indicator should appear
    await expect(page.locator("[data-testid='typing-indicator']")).toBeVisible();
    // Then disappear when done
    await expect(page.locator("[data-testid='typing-indicator']")).toBeHidden({ timeout: 60000 });
  });

  test("clear conversation resets chat", async ({ page }) => {
    const input = page.locator("[data-testid='chat-input']");
    await input.fill("Hello");
    await page.keyboard.press("Enter");
    await page.waitForSelector("[data-testid='message-bubble-assistant']", { timeout: 30000 });

    await page.click("[data-testid='clear-chat-button']");
    await expect(page.locator("[data-testid='message-bubble']")).toHaveCount(0);
  });

  test("suggestion chip click sends message", async ({ page }) => {
    await page.waitForSelector("[data-testid='suggestion-chip']", { timeout: 10000 });
    const firstChip = page.locator("[data-testid='suggestion-chip']").first();
    const chipText = await firstChip.textContent();
    await firstChip.click();

    const lastUserMessage = page.locator("[data-testid='message-bubble-user']").last();
    await expect(lastUserMessage).toContainText(chipText || "");
  });

  test("error state displays friendly message", async ({ page }) => {
    // Simulate network error by blocking API
    await page.route("**/api/bff/ai/chat", (route) => route.abort("internetdisconnected"));

    const input = page.locator("[data-testid='chat-input']");
    await input.fill("Hello");
    await page.keyboard.press("Enter");

    await expect(page.locator("[data-testid='error-message']")).toContainText(/unavailable|error/i);
  });

  test("RTL layout for Arabic input", async ({ page }) => {
    const input = page.locator("[data-testid='chat-input']");
    await input.fill("مرحبا كيف حالك");
    await expect(input).toHaveAttribute("dir", "rtl");
  });
});
