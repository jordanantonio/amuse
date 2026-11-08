import { expect, test, type Page } from '@playwright/test';

export async function signInAs(page: Page, name: RegExp) {
  await page.goto('/signin/demo');
  await page.getByRole('button', { name }).click();
  await expect(page).toHaveURL(/\/home$/);
}

test('worker wallet: expiring warning, add a ticket with proof, four-tab nav', async ({ page }) => {
  await signInAs(page, /Maya Brooks/);
  await expect(page.getByRole('link', { name: /WHMIS expires/ })).toBeVisible();
  const nav = page.locator('.v1-nav').getByRole('link');
  await expect(nav).toHaveText(['Home', 'Work', 'Schedule', 'Profile']);
  await page.getByRole('link', { name: 'Profile', exact: true }).first().click();
  await expect(page.getByRole('heading', { name: 'Maya Brooks' })).toBeVisible();
  const whmis = page.locator('.wallet-card').filter({ hasText: 'WHMIS' });
  await expect(whmis).toContainText('Expires in 6 days');
  await expect(whmis).toContainText('Verified');
  await page.screenshot({ path: 'test-results/v1-profile-desktop.png', fullPage: true });

  await page.getByRole('button', { name: 'Add ticket' }).click();
  const dialog = page.getByRole('dialog', { name: 'Add a ticket' });
  await dialog.getByLabel('Type').selectOption('fall-protection');
  await dialog.getByLabel('Expires on').fill('2029-03-31');
  await dialog.locator('input[type=file]').setInputFiles({
    name: 'fall-protection.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4\n% fall protection card\n'),
  });
  await dialog.getByRole('button', { name: 'Save' }).click();
  await expect(dialog).toHaveCount(0);
  const fall = page.locator('.wallet-card').filter({ hasText: 'Fall Protection' });
  await expect(fall).toContainText('Pending review');
  await expect(fall).toContainText('fall-protection.pdf');

  await page.setViewportSize({ width: 390, height: 844 });
  const tabbar = page.locator('.v1-tabbar');
  await expect(tabbar).toBeVisible();
  await expect(tabbar.getByRole('link')).toHaveCount(4);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ path: 'test-results/v1-profile-mobile.png', fullPage: true });
});

test('business sees its company profile and credentials', async ({ page }) => {
  await signInAs(page, /Alex Morgan/);
  await page.getByRole('link', { name: 'Profile', exact: true }).first().click();
  await expect(page.getByRole('heading', { name: 'Northline Homes' })).toBeVisible();
  await expect(page.locator('.wallet-card').filter({ hasText: 'COR' })).toContainText('Verified');
});
