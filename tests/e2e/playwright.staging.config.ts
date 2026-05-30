import { defineConfig, devices } from "@playwright/test";
import stagingConfig from "./staging.config";

/**
 * Playwright configuration for staging E2E tests.
 */
export default defineConfig({
  testDir: "./specs",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: stagingConfig.retries,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ["html", { outputFolder: "playwright-report-staging" }],
    ["junit", { outputFile: "test-results/staging-e2e.xml" }],
  ],
  use: {
    baseURL: stagingConfig.baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "on-first-retry",
    extraHTTPHeaders: {
      "X-Tenant-Id": stagingConfig.tenant.id,
      "X-Correlation-Id": `e2e-${Date.now()}`,
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
    {
      name: "Mobile Chrome",
      use: { ...devices["Pixel 5"] },
    },
    {
      name: "Mobile Safari",
      use: { ...devices["iPhone 12"] },
    },
  ],
});
