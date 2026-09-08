import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:8765",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "android-chromium", use: { ...devices["Pixel 7"] } },
    { name: "iphone-webkit", use: { ...devices["iPhone 13"] } },
  ],
  webServer: {
    command:
      "../../services/backend/.venv/bin/python ../../scripts/e2e_server.py",
    url: "http://127.0.0.1:8765/healthz",
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
