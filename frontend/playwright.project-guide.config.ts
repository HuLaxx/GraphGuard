import { defineConfig, devices } from "@playwright/test";

const port = Number(process.env.PROJECT_GUIDE_PORT || 3123);

/** Runs only e2e/project-guide.spec.ts against a local Next.js dev server. */
export default defineConfig({
  testDir: "./e2e",
  testMatch: /project-guide\.spec\.ts/,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: `http://localhost:${port}`, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `npx next dev --port ${port}`,
    url: `http://localhost:${port}/api/project-guide`,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    env: { ASSISTANT_LLM_DISABLED: "1" },
  },
});
