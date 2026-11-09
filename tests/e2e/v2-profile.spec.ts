import { expect, test } from '@playwright/test';
import { signInAs } from './helpers';

test.beforeEach(async ({ request }) => {
  expect((await request.post('/api/v1/dev/reset')).ok()).toBeTruthy();
});

test('Ilya profile: banner, availability, about, experience, certs, reviews; inline edit', async ({
  page,
}) => {
  await signInAs(page, 'u-ilya');
  await page.goto('/profile');
  await expect(page.getByRole('heading', { name: 'Ilya Sukhanov' })).toBeVisible();
  await expect(page.locator('.avail-pill')).toHaveText('Open to work now');
  await expect(page.locator('.lprofile-about')).toContainText('night shift needs to run clean');
  const exp = page.locator('.timeline > li').filter({ hasText: 'Sanitation shutdown crew' });
  await expect(exp).toContainText('Completed on Shift');
  await expect(exp.getByRole('img', { name: '5 out of 5 stars' })).toBeVisible();
  await expect(page.locator('.gallery img').first()).toBeVisible();
  await expect(page.locator('.review')).toHaveCount(3);
  await expect(page.getByRole('button', { name: 'Upload certification' })).toBeVisible();
  const bg = await page.locator('.v1-shell').evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(bg).toBe('rgb(0, 82, 177)');
  await page.screenshot({ path: 'test-results/v2-profile.png', fullPage: true });

  await page.getByRole('button', { name: 'Edit Languages' }).click();
  await page.getByRole('textbox', { name: /Languages/ }).fill('English, Russian, French');
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page.locator('.lprofile-section').filter({ hasText: 'Languages' })).toContainText(
    'French',
  );

  await page.getByRole('button', { name: 'Upload certification' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Type').selectOption('fall-protection');
  await dialog.locator('input[type=file]').setInputFiles({
    name: 'fall.png',
    mimeType: 'image/png',
    buffer: Buffer.from(
      '89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8ffff3f0005fe02fea7d6a4a80000000049454e44ae426082',
      'hex',
    ),
  });
  await expect(dialog.getByAltText('Preview of the selected certification')).toBeVisible();
});
