import { defineConfig } from '@playwright/test';

// Migration histories can differ between branches; keep each run isolated.
const fixture = `.tmp/e2e-${Date.now()}-${process.pid}`;
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: 'http://127.0.0.1:3000',
    headless: true,
    trace: 'retain-on-failure',
    launchOptions: process.env.PLAYWRIGHT_CHROME_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROME_PATH }
      : {},
  },
  webServer: [
    {
      command: 'uv run python scripts/dev_api.py',
      url: 'http://127.0.0.1:8000/api/v1/health',
      reuseExistingServer: false,
      env: {
        SHIFT_DATABASE_URL: `sqlite:///./${fixture}.sqlite`,
        SHIFT_UPLOAD_DIR: `${fixture}-uploads`,
        SHIFT_DEMO_MODE: 'true',
      },
      timeout: 30000,
    },
    {
      command: 'npm run dev',
      url: 'http://127.0.0.1:3000',
      reuseExistingServer: false,
      timeout: 90000,
      env: { NEXT_TELEMETRY_DISABLED: '1' },
    },
  ],
});
