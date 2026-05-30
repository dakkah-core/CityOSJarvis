import { defineConfig } from "@playwright/test";

/**
 * Playwright config for AI Stack E2E tests.
 *
 * Usage:
 *   npx playwright test --config=e2e/ai-stack/playwright.config.ts
 */

export default defineConfig({
  testDir: ".",
  fullyParallel: false, // Sequential — rate limits + shared infra
  workers: 1,
  retries: 1,
  timeout: 30_000,
  reporter: [["list"], ["html", { outputFolder: "../../e2e-reports/ai-stack" }]],
  use: {
    baseURL: process.env.E2E_JARVIS_URL || "http://localhost:8000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "ai-stack",
      use: {},
    },
  ],
});
