import { expect, test } from '@playwright/test';

test('signed-out visitors are sent from Home to the landing page', async ({ page }) => {
  await page.goto('/home');
  await expect(page).toHaveURL(/\/\?next=%2Fhome$/);
  await expect(
    page.locator('.public-nav').getByRole('link', { name: 'Sign in', exact: true }),
  ).toBeVisible();
});

test('new worker signs in, onboards in three steps and lands on Home', async ({ page }) => {
  await page.goto('/');
  await page.locator('.public-nav').getByRole('link', { name: 'Sign in', exact: true }).click();
  // No Google client is configured in tests, so the honest demo fallback appears.
  await expect(page.getByRole('heading', { name: 'How do you want to use Shift?' })).toBeVisible();
  await page.waitForLoadState('networkidle');
  await page.getByRole('button', { name: 'or create a new account' }).click();
  await page.getByLabel('Your name').fill('Jordan Kay');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('heading', { name: 'How will you use Shift?' })).toBeVisible();
  await page.getByRole('button', { name: /I’m looking for work/ }).click();
  await expect(page.getByText('Step 1 of 3')).toBeVisible();
  await page.getByLabel('Headline').fill('Structural welder, 6 yrs');
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByText('Welding', { exact: true }).click();
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByLabel('Home city').selectOption('Leduc');
  await page.getByRole('button', { name: 'Finish' }).click();
  await expect(page).toHaveURL(/\/home$/);
  await expect(page.getByRole('heading', { name: /Jordan/ })).toBeVisible();
  // Session survives a refresh.
  await page.reload();
  await expect(page.getByRole('heading', { name: /Jordan/ })).toBeVisible();
});

test('the demo picker shows three personas and signs Ilya in', async ({ page }) => {
  await page.goto('/');
  await expect(
    page.getByRole('heading', { name: 'Find skilled trades work across Alberta' }),
  ).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Open contracts', exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/v2-landing.png' });
  await expect(
    page.getByText('Fictional demo. All companies, people and contracts shown are made up.'),
  ).toBeVisible();
  await page.locator('.public-nav').getByRole('link', { name: 'Sign in', exact: true }).click();
  const cards = page.locator('.persona-card');
  await expect(cards).toHaveCount(3);
  await expect(cards.nth(1)).toContainText('Prairie Harvest Foods');
  await expect(cards.nth(2)).toContainText('Timberline Framing Crew');
  await page.screenshot({ path: 'test-results/v2-picker.png', fullPage: true });
  await page.waitForLoadState('networkidle');
  await cards.filter({ hasText: 'I’m looking for work' }).click();
  await expect(page).toHaveURL(/\/home$/);
  await expect(page.getByRole('heading', { name: /Ilya/ })).toBeVisible();
});
