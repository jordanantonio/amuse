import { expect, test } from '@playwright/test';

test('signed-out visitors are sent from Home to the landing page', async ({ page }) => {
  await page.goto('/home');
  await expect(page).toHaveURL(/\/\?next=%2Fhome$/);
  await expect(page.getByRole('link', { name: 'Continue with Google' })).toBeVisible();
});

test('new worker signs in, onboards in three steps and lands on Home', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Continue with Google' }).click();
  // No Google client is configured in tests, so the honest demo fallback appears.
  await expect(page.getByRole('heading', { name: 'Choose a demo account' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Maya Brooks/ })).toBeVisible();
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

test('a seeded worker signs in through the demo chooser', async ({ page }) => {
  await page.goto('/signin/demo');
  await page.getByRole('button', { name: /Maya Brooks/ }).click();
  await expect(page).toHaveURL(/\/home$/);
});
