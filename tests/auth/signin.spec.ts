import { test, expect, type Page } from '@playwright/test';

const user = {
  id: '00000000-0000-4000-8000-000000000001',
  aud: 'authenticated',
  role: 'authenticated',
  email: 'manager@example.test',
  app_metadata: {},
  user_metadata: {},
  created_at: '2026-11-01T00:00:00Z',
};
function session(marker = 'initial') {
  const payload = { sub: user.id, exp: Math.floor(Date.now() / 1000) + 3600, marker };
  const token = [
    Buffer.from(JSON.stringify({ alg: 'RS256' })).toString('base64url'),
    Buffer.from(JSON.stringify(payload)).toString('base64url'),
    'fictional-signature',
  ].join('.');
  return {
    access_token: token,
    token_type: 'bearer',
    refresh_token: 'fictional-refresh-token',
    expires_in: 3600,
    expires_at: payload.exp,
    user,
  };
}
async function mockServices(page: Page, membership = true) {
  let refreshes = 0;
  await page.route('https://fictional.supabase.co/auth/v1/**', async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/logout')) return route.fulfill({ json: {} });
    if (url.searchParams.get('grant_type') === 'refresh_token') {
      refreshes++;
      return route.fulfill({ json: session('refreshed') });
    }
    if (route.request().postDataJSON()?.password !== 'fictional-password') {
      return route.fulfill({
        status: 400,
        json: { code: 'invalid_credentials', message: 'Invalid login credentials' },
      });
    }
    return route.fulfill({ json: session() });
  });
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/health')) return route.fulfill({ json: { demo: false } });
    expect(route.request().headers()['x-demo-persona']).toBeUndefined();
    expect(route.request().headers().authorization).toMatch(/^Bearer /);
    if (!membership)
      return route.fulfill({
        status: 403,
        json: { detail: 'No organization membership. Contact your administrator.' },
      });
    const persona = { id: user.id, name: 'Fictional Manager', role: 'manager' };
    if (path.endsWith('/me'))
      return route.fulfill({
        json: {
          persona,
          organization_id: 'fictional',
          organization: 'Fictional Works',
          demo: false,
        },
      });
    return route.fulfill({
      json: {
        organization: 'Fictional Works',
        persona,
        demo: false,
        week_start: '2026-11-09',
        timezone: 'America/Edmonton',
        workers: [],
        projects: [],
        assignments: [],
        jobs: [],
        staffing_gaps: 0,
      },
    });
  });
  return () => refreshes;
}
async function login(page: Page, password = 'fictional-password') {
  await page.getByLabel('Email', { exact: true }).fill('manager@example.test');
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
}

test('password errors, sign-in, restored session and sign-out', async ({ page }) => {
  await mockServices(page);
  await page.goto('/');
  await login(page, 'wrong-password');
  await expect(page.locator('.auth-card').getByRole('alert')).toContainText('Invalid login credentials');
  await login(page);
  await expect(page.getByRole('heading', { name: 'Good morning, Fictional.' })).toBeVisible();
  await expect(page.getByLabel('Demo persona')).toHaveCount(0);
  await expect(page.getByText('FICTIONAL DEMO')).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Good morning, Fictional.' })).toBeVisible();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await expect(page.getByText('Fictional Works')).toHaveCount(0);
});

test('missing membership is actionable and does not expose workspace', async ({ page }) => {
  await mockServices(page, false);
  await page.goto('/');
  await login(page);
  await expect(page.locator('.auth-card').getByRole('alert')).toContainText('No organization membership');
  await expect(page.locator('.app-shell')).toHaveCount(0);
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
});

test('refreshes an expired stored session and clears workspace on expiry', async ({ page }) => {
  const refreshes = await mockServices(page);
  await page.goto('/');
  await login(page);
  await expect(page.locator('.app-shell')).toBeVisible();
  await page.evaluate(() => {
    const key = Object.keys(localStorage).find((key) => key.endsWith('-auth-token'))!;
    const stored = JSON.parse(localStorage.getItem(key)!);
    stored.expires_at = 1;
    localStorage.setItem(key, JSON.stringify(stored));
  });
  await page.reload();
  await expect(page.locator('.app-shell')).toBeVisible();
  expect(refreshes()).toBeGreaterThan(0);
  await page.evaluate(() => window.dispatchEvent(new Event('shift-session-expired')));
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await expect(page.locator('.auth-card').getByRole('alert')).toContainText('Session expired');
  await expect(page.locator('.app-shell')).toHaveCount(0);
});
