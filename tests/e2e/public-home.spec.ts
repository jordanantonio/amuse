import { expect, test } from '@playwright/test';

test.beforeEach(async ({ request }) => {
  expect((await request.post('/api/v1/dev/reset')).ok()).toBeTruthy();
});

test('public home works without a session: search, trade filtering and preview', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(
    page.getByRole('heading', { name: 'Find skilled trades work across Alberta' }),
  ).toBeVisible();
  await expect(page.locator('.public-contract').first()).toBeVisible();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('button', { name: 'Previous contracts' })).toBeDisabled();
  await page.getByRole('button', { name: 'Next contracts' }).click();
  await expect(page.getByRole('button', { name: 'Previous contracts' })).toBeEnabled();
  await page.getByLabel('Search trades, contracts or cities').fill('Electrical');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await expect(page.locator('.public-filter-note')).toContainText('Electrical');
  await expect(page.locator('.public-contract').first()).toBeVisible();
  await page.getByRole('button', { name: 'Electrical', exact: true }).click();
  const card = page.locator('.public-contract').first();
  await card.locator('.public-contract-link').click();
  const preview = page.getByRole('dialog');
  await expect(preview).toBeVisible();
  await expect(preview).toContainText('Exact site addresses are shared only with offers');
  const destination = await preview
    .getByRole('link', { name: 'Sign in to view and apply' })
    .getAttribute('href');
  expect(destination).toMatch(/^\/api\/v1\/auth\/google\/start\?next=%2Fpostings%2F/);
  await page.keyboard.press('Escape');
  await expect(preview).toHaveCount(0);
  await page.getByLabel('Search trades, contracts or cities').fill('no-such-trade-19384');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'No contracts match this search' })).toBeVisible();
  await page.getByRole('button', { name: 'View all contracts' }).click();
  await expect(page.locator('.public-contract').first()).toBeVisible();
  expect(errors).toEqual([]);
});

test('saved contracts persist locally and root stays public after signing in', async ({ page }) => {
  await page.goto('/');
  const save = page.locator('.public-save').first();
  await expect(save).toBeVisible();
  await save.click();
  await expect(save).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('status').filter({ hasText: 'saved on this device' })).toBeVisible();
  await page.reload();
  await expect(page.locator('.public-save').first()).toHaveAttribute('aria-pressed', 'true');
  await page.request.post('/api/v1/auth/demo', { data: { user_id: 'u-ilya' } });
  await page.goto('/');
  await expect(
    page.getByRole('heading', { name: 'Find skilled trades work across Alberta' }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/$/);
});

test('public home is usable on mobile and handles API failure and retry', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/api/v1/public/contracts?*', (route) =>
    route.fulfill({
      status: 503,
      json: { detail: 'The contract service is temporarily unavailable.' },
    }),
  );
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Contracts couldn’t load' })).toBeVisible();
  await page.unroute('**/api/v1/public/contracts?*');
  await page.getByRole('button', { name: 'Try again' }).click();
  await expect(page.locator('.public-contract').first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ path: 'test-results/public-home-mobile.png', fullPage: true });
});

test('public listing sign-in returns to the selected contract', async ({ page }) => {
  await page.goto('/');
  await page.locator('.public-contract-link').first().click();
  const link = page.getByRole('dialog').getByRole('link', { name: 'Sign in to view and apply' });
  const target = new URL((await link.getAttribute('href'))!, 'http://localhost').searchParams.get(
    'next',
  );
  await link.click();
  await expect(page).toHaveURL(/\/signin\/demo\?next=/);
  await page.waitForLoadState('networkidle');
  await page.locator('.persona-card').filter({ hasText: 'I’m looking for work' }).click();
  await expect(page).toHaveURL(new RegExp(`${target}$`), { timeout: 15000 });
});
