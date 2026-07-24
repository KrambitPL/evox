import { defineConfig, devices } from "@playwright/test";
import { devices as replayDevices, replayReporter } from "@replayio/playwright";

const baseURL = process.env.EVOX_E2E_BASE_URL;

if (!baseURL) {
  throw new Error(
    "EVOX_E2E_BASE_URL is required. Point it at a real, explicitly configured Evox environment.",
  );
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter:
    process.env.EVOX_REPLAY_UPLOAD === "true"
      ? [
          replayReporter({
            apiKey: process.env.REPLAY_API_KEY,
            upload: true,
          }),
          ["line"],
        ]
      : [["line"]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "replay-chromium", use: { ...replayDevices["Replay Chromium"] } },
  ],
});
