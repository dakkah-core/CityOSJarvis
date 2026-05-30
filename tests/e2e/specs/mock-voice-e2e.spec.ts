/**
 * Mock-based E2E tests for voice pipeline.
 * Does NOT require Twilio credentials — uses mocked STT/TTT responses.
 */

import { test, expect } from "@playwright/test";

test.describe("Voice Pipeline (Mock)", () => {
  test.beforeEach(async ({ page }) => {
    // Mock the STT endpoint
    await page.route("**/v1/voice/stt", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          text: "What is the weather like today?",
          language: "en",
          probability: 0.98,
        }),
      });
    });

    // Mock the TTS endpoint
    await page.route("**/v1/voice/speak", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          audio_url: "https://mock.cdn.example.com/audio-123.mp3",
          duration_ms: 2500,
        }),
      });
    });

    // Mock chat response
    await page.route("**/v1/chat", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          content: "The weather today is sunny with a high of 32°C.",
          tool_results: [],
        }),
      });
    });
  });

  test("voice orb cycles through states on click", async ({ page }) => {
    await page.goto("http://localhost:3000/ai-assistant");

    const voiceOrb = page.locator('[data-testid="voice-orb"]').first();
    await expect(voiceOrb).toBeVisible();

    // Click to start listening
    await voiceOrb.click();
    await expect(voiceOrb).toHaveAttribute("data-state", "listening");

    // After mock STT delay, should transition to processing
    await expect(voiceOrb).toHaveAttribute("data-state", "processing");

    // After mock chat response, should be speaking
    await expect(voiceOrb).toHaveAttribute("data-state", "speaking");
  });

  test("voice input captures transcript", async ({ page }) => {
    await page.goto("http://localhost:3000/ai-assistant");

    // Simulate voice input via mock
    await page.evaluate(() => {
      window.dispatchEvent(
        new CustomEvent("voice-transcript", {
          detail: { transcript: "Book a taxi to the airport" },
        })
      );
    });

    const chatInput = page.locator('[data-testid="chat-input"]').first();
    await expect(chatInput).toHaveValue("Book a taxi to the airport");
  });

  test("TTS plays audio response", async ({ page }) => {
    await page.goto("http://localhost:3000/ai-assistant");

    // Send a message that triggers TTS
    await page.fill('[data-testid="chat-input"]', "Tell me the news");
    await page.click('[data-testid="send-button"]', { force: true });

    // Should show audio player or TTS indicator
    await expect(page.locator('[data-testid="tts-audio"]').first()).toBeVisible({ timeout: 5000 });
  });

  test("voice error state shows retry option", async ({ page }) => {
    // Override STT mock to return error
    await page.route("**/v1/voice/stt", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Speech recognition failed" }),
      });
    });

    await page.goto("http://localhost:3000/ai-assistant");

    const voiceOrb = page.locator('[data-testid="voice-orb"]').first();
    await voiceOrb.click();

    // Should show error state
    await expect(page.locator('[data-testid="voice-error"]').first()).toBeVisible();

    // Should show retry button
    await expect(page.locator('[data-testid="voice-retry"]').first()).toBeVisible();
  });

  test("Arabic voice input works", async ({ page }) => {
    await page.route("**/v1/voice/stt", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          text: "ما هو الطقس اليوم؟",
          language: "ar",
          probability: 0.97,
        }),
      });
    });

    await page.goto("http://localhost:3000/ai-assistant?lang=ar");

    await page.evaluate(() => {
      window.dispatchEvent(
        new CustomEvent("voice-transcript", {
          detail: { transcript: "ما هو الطقس اليوم؟", language: "ar" },
        })
      );
    });

    const chatInput = page.locator('[data-testid="chat-input"]').first();
    await expect(chatInput).toHaveValue("ما هو الطقس اليوم؟");
  });
});
