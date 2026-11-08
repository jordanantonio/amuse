import { expect, test } from '@playwright/test';
import { signInAs } from './helpers';

test.beforeEach(async ({ request }) => {
  expect((await request.post('/api/v1/dev/reset')).ok()).toBeTruthy();
});

test('blueprint shell: bright new-contract card on top, faces on cards', async ({ page }) => {
  await signInAs(page, 'u-ilya');
  const first = page.locator('.v1-main > *').nth(1);
  await expect(first).toHaveClass(/new-since/);
  await expect(first).toContainText('1 new contract fits you since yesterday');
  await expect(
    page.locator('.feed-list .contract-card').first().locator('.company-badge'),
  ).toBeVisible();
  const bg = await page.locator('.v1-shell').evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(bg).toBe('rgb(0, 60, 118)');
  await page.screenshot({ path: 'test-results/v2-home-ilya.png', fullPage: true });
});

test('business rows show worker avatars; theme preview lists both blues', async ({ page }) => {
  await signInAs(page, 'u-rahul');
  await page.goto('/work?tab=applicants');
  await expect(page.locator('.applicant-row .person-avatar').first()).toBeVisible();
  await page.screenshot({ path: 'test-results/v2-work-rahul.png', fullPage: true });
  await page.goto('/dev/theme');
  await expect(page.getByRole('heading', { name: /Deeper blueprint/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: /Vibrant blueprint/ })).toBeVisible();
  await page.screenshot({ path: 'test-results/v2-theme.png', fullPage: true });
});
