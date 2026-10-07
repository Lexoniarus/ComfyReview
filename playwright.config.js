import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.COMFYREVIEW_E2E_URL || "http://127.0.0.1:8015";

export default defineConfig({
  testDir: "./frontend-e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "line",
  use: {
    baseURL,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "off",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: {
          args: ["--host-resolver-rules=MAP comfyreview.test 127.0.0.1"],
        },
      },
    },
  ],
  outputDir: "test-results/playwright",
  webServer: {
    command: "python frontend-e2e/support/e2e_server.py",
    url: `${baseURL}/_e2e/health`,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
