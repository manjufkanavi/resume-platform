import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E config for the resume-platform Next.js SPA.
 * Run against a live backend: `npm run dev` (port 3007), then
 * `npx playwright test`. The demo fallback in the UI lets most flows run
 * without a backend; the Keycloak/real-token flows need the real stack.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:3007",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
