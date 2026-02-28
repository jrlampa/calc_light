import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E configuration for CACL LIGHT frontend.
 * Tests run headless against the Vite dev server on port 5173.
 * The backend is fully mocked via page.route() interceptors.
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',

  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    // Vite typically starts in < 5s, but allow extra time in slow CI environments
    timeout: 120_000,
  },
});
