import { test, expect } from "@playwright/test";

test.describe("Accessibility E2E (axe-core)", () => {
  test("chat widget passes axe scan", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("[data-testid='chat-input']");

    // Inject axe-core
    await page.addScriptTag({
      path: require.resolve("axe-core/axe.min.js"),
    });

    const results = await page.evaluate(async () => {
      // @ts-ignore
      return await axe.run();
    });

    expect(results.violations).toHaveLength(0);
  });

  test("keyboard navigation works", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("[data-testid='chat-input']");

    // Tab to voice button
    await page.keyboard.press("Tab");
    await expect(page.locator("[data-testid='voice-button']")).toBeFocused();

    // Tab to settings
    await page.keyboard.press("Tab");
    await expect(page.locator("[data-testid='settings-button']")).toBeFocused();

    // Tab to chat input
    await page.keyboard.press("Tab");
    await expect(page.locator("[data-testid='chat-input']")).toBeFocused();
  });

  test("ARIA labels present on interactive elements", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("[data-testid='chat-input']");

    const voiceButton = page.locator("[data-testid='voice-button']");
    await expect(voiceButton).toHaveAttribute("aria-label", /.+/);

    const sendButton = page.locator("[data-testid='send-button']");
    await expect(sendButton).toHaveAttribute("aria-label", /.+/);
  });

  test("color contrast meets WCAG AA", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("[data-testid='chat-input']");

    await page.addScriptTag({
      path: require.resolve("axe-core/axe.min.js"),
    });

    const results = await page.evaluate(async () => {
      // @ts-ignore
      return await axe.run({
        runOnly: ["color-contrast"],
      });
    });

    expect(results.violations).toHaveLength(0);
  });

  test("RTL mode screen reader friendly", async ({ page }) => {
    await page.goto("/?lang=ar");
    await page.waitForSelector("[data-testid='chat-input']");

    const html = page.locator("html");
    await expect(html).toHaveAttribute("lang", "ar");
    await expect(html).toHaveAttribute("dir", "rtl");
  });
});
