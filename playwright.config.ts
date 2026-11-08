import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: 'http://127.0.0.1:3002',
    headless: true,
    trace: 'retain-on-failure',
    launchOptions: process.env.PLAYWRIGHT_CHROME_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROME_PATH }
      : {},
  },
  webServer: [
    {
      command: 'uv run python scripts/dev_api.py',
      url: 'http://127.0.0.1:8002/api/v1/health',
      reuseExistingServer: false,
      env: {
        SHIFT_DATABASE_URL: 'sqlite:///./.tmp/e2e.sqlite',
        SHIFT_DEMO_MODE: 'true',
        SHIFT_ENVIRONMENT: 'local',
        SHIFT_DEMO_PORT: '8002',
      },
      timeout: 30000,
    },
    {
      command: 'npm run dev --workspace=@shift/web -- --port 3002',
      url: 'http://127.0.0.1:3002',
      reuseExistingServer: false,
      timeout: 90000,
      env: {
        NEXT_TELEMETRY_DISABLED: '1',
        SHIFT_NEXT_DIST_DIR: '.next-e2e-tests',
        API_INTERNAL_URL: 'http://127.0.0.1:8002',
      },
    },
  ],
});
