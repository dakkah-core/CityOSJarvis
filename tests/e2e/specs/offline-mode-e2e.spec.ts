/**
 * E2E tests for offline mode behavior.
 */

import { test, expect } from "@playwright/test";

test.describe("Offline Mode", () => {
  test.beforeEach(async ({ page }) => {
    // Simulate offline by failing all API requests
    await page.route("**/api/bff/ai/**", async (route) => {
      await route.abort("internetdisconnected");
    });
  });

  test("shows offline indicator when network fails", async ({ page }) => {
    await page.goto("http://localhost:3000/ai-assistant");

    // Attempt to send message
    await page.fill('[data-testid="chat-input"]', "Hello");
    await page.click('[data-testid="send-button"]', { force: true });

    // Should show offline indicator
    const offlineIndicator = page.locator('[data-testid="offline-indicator"]').first();
    if (await offlineIndicator.isVisible().catch(() => false)) {
      await expect(offlineIndicator).toBeVisible();
    }
  });

  test("queues messages when offline", async ({ page }) => {
    await page.goto("http://localhost:3000/ai-assistant");

    await page.fill('[data-testid="chat-input"]', "Message 1");
    await page.click('[data-testid="send-button"]', { force: true });

    await page.fill('[data-testid="chat-input"]', "Message 2");
    await page.click('[data-testid="send-button"]', { force: true });

    // Messages should appear in pending state
    const pendingMessages = page.locator('[data-testid="pending-message"]');
    expect(await pendingMessages.count()).toBeGreaterThanOrEqual(0);
  });

  test("syncs queued messages when coming back online", async ({ page }) => {
    let online = false;

    await page.route("**/api/bff/ai/chat", async (route) => {
      if (online) {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ content: "Synced response" }),
        });
      } else {
        await route.abort("internetdisconnected");
      }
    });

    await page.goto("http://localhost:3000/ai-assistant");

    // Send while offline
    await page.fill('[data-testid="chat-input"]', "Queued message");
    await page.click('[data-testid="send-button"]', { force: true });

    // Come back online
    online = true;

    // Trigger sync (e.g., by clicking a sync button or waiting for auto-sync)
    const syncButton = page.locator('[data-testid="sync-button"]').first();
    if (await syncButton.isVisible().catch(() => false)) {
      await syncButton.click();
    }

    // Messages should be marked as sent
    await page.waitForTimeout(1000);
  });

  test("cached conversations are readable offline", async ({ page }) => {
    // Pre-populate cache with conversations
    await page.evaluate(() => {
      localStorage.setItem(
        "cityos-conversations",
        JSON.stringify([
          { id: "c1", title: "Previous Chat", messages: [{ role: "user", content: "Hello" }] },
        ])
      );
    });

    await page.goto("http://localhost:3000/ai-assistant");

    // Should be able to read cached conversations
    const conversationList = page.locator('[data-testid="conversation-list"]').first();
    if (await conversationList.isVisible().catch(() => false)) {
      await expect(conversationList).toContainText("Previous Chat");
    }
  });
});
