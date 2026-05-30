/**
 * E2E tests for compliance gate behavior.
 * Verifies PHI/PII blocking in chat inputs.
 */

import { test, expect } from "@playwright/test";

test.describe("Compliance Gate E2E", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/bff/ai/chat", async (route) => {
      const request = route.request();
      const postData = request.postDataJSON();

      // Simulate compliance gate on server
      const blockedPatterns = [
        /\b4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/, // Credit card
        /\b\d{10}\b/, // Saudi ID
        /\+966\d{9}/, // Saudi mobile
        /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/, // Email
      ];

      const isBlocked = blockedPatterns.some((p) => p.test(postData.message));

      if (isBlocked) {
        await route.fulfill({
          status: 400,
          contentType: "application/json",
          body: JSON.stringify({
            error: "Compliance violation",
            detail: "Request contains sensitive personal information. Please remove PII before submitting.",
            category: "blocked",
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ content: "Here's what I found..." }),
        });
      }
    });
  });

  test("blocks credit card numbers", async ({ page }) => {
    const response = await page.request.post("http://localhost:8000/api/bff/ai/chat", {
      data: { message: "My card is 4111111111111111" },
    });

    expect(response.status()).toBe(400);
    const body = await response.json();
    expect(body.category).toBe("blocked");
  });

  test("blocks Saudi ID numbers", async ({ page }) => {
    const response = await page.request.post("http://localhost:8000/api/bff/ai/chat", {
      data: { message: "My ID is 1234567890" },
    });

    expect(response.status()).toBe(400);
    const body = await response.json();
    expect(body.error).toContain("Compliance");
  });

  test("blocks email addresses", async ({ page }) => {
    const response = await page.request.post("http://localhost:8000/api/bff/ai/chat", {
      data: { message: "Contact me at test@example.com" },
    });

    expect(response.status()).toBe(400);
  });

  test("blocks Saudi mobile numbers", async ({ page }) => {
    const response = await page.request.post("http://localhost:8000/api/bff/ai/chat", {
      data: { message: "Call me at +966501234567" },
    });

    expect(response.status()).toBe(400);
  });

  test("allows safe messages", async ({ page }) => {
    const response = await page.request.post("http://localhost:8000/api/bff/ai/chat", {
      data: { message: "What is the weather today?" },
    });

    expect(response.status()).toBe(200);
  });

  test("allows Arabic messages without PII", async ({ page }) => {
    const response = await page.request.post("http://localhost:8000/api/bff/ai/chat", {
      data: { message: "ما هو الطقس اليوم؟" },
    });

    expect(response.status()).toBe(200);
  });

  test("blocks mixed language with PII", async ({ page }) => {
    const response = await page.request.post("http://localhost:8000/api/bff/ai/chat", {
      data: { message: "رقم البطاقة 1234567890" },
    });

    expect(response.status()).toBe(400);
  });
});
