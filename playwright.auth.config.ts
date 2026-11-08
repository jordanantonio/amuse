import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/auth',
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: 'http://127.0.0.1:3001',
    headless: true,
    trace: 'retain-on-failure',
    launchOptions: process.env.PLAYWRIGHT_CHROME_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROME_PATH }
      : {},
  },
  webServer: {
    command: 'npm run dev:hosted --workspace=@shift/web -- --port 3001',
    url: 'http://127.0.0.1:3001',
    reuseExistingServer: false,
    timeout: 90000,
    env: {
      NEXT_TELEMETRY_DISABLED: '1',
      SHIFT_NEXT_DIST_DIR: '.next-auth-tests',
      NEXT_PUBLIC_SUPABASE_URL: 'https://fictional.supabase.co',
      NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: 'fictional-public-key-for-ui-tests',
    },
  },
});
