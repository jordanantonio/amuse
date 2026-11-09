import { expect, test } from '@playwright/test';
import { signInAs } from './helpers';

test.beforeEach(async ({ request }) => {
  expect((await request.post('/api/v1/dev/reset')).ok()).toBeTruthy();
});

test('crew planner: assign with fatigue advice, auto-fill, find a replacement', async ({
  page,
}) => {
  await signInAs(page, 'u-rahul');
  await page.goto('/work');
  await page
    .getByRole('link', { name: /Crew planner/ })
    .first()
    .click();
  await expect(page.getByRole('heading', { name: 'Crew planner' })).toBeVisible();
  const days = page.locator('.crew-day');
  await expect(days).toHaveCount(7);
  const wed = days.nth(2);
  const wedAm = wed.locator('.slot-card').filter({ hasText: '8 AM–12 PM' });
  await wedAm
    .getByRole('button', { name: /Open spot/ })
    .first()
    .click();
  const sheet = page.getByRole('dialog', { name: /Candidates for Packaging line/ });
  const ilya = sheet.locator('.candidate').filter({ hasText: 'Ilya Sukhanov' });
  await expect(ilya).toContainText('Would be 3rd day in a row');
  await expect(ilya.locator('.avail-bar')).toBeVisible();
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'test-results/v2-crew-panel.png' });
  await ilya.getByRole('button', { name: 'Assign' }).click();
  await expect(sheet).toHaveCount(0);
  await expect(wedAm.getByRole('button', { name: 'Ilya Sukhanov' })).toBeVisible();

  await page.getByRole('button', { name: 'Auto-fill week' }).click();
  await expect(page.locator('.proposal-bar')).toContainText('Auto-fill proposed');
  await expect(page.locator('.spot.proposed').first()).toBeVisible();
  const sunday = days.nth(6).locator('.slot-card').filter({ hasText: 'Cold storage restock' });
  await sunday.getByRole('button', { name: 'Find a replacement' }).click();
  const market = page.getByRole('dialog', { name: /Candidates for Cold storage restock/ });
  const liam = market.locator('.candidate').first();
  await expect(liam).toContainText('Liam Patel');
  await liam.getByRole('button', { name: 'Assign' }).click();
  await expect(sunday.getByRole('button', { name: 'Liam Patel' })).toBeVisible();
  await page.screenshot({ path: 'test-results/v2-crew-board.png', fullPage: true });
  await page.getByRole('button', { name: 'Accept all' }).click();
  await expect(page.locator('.proposal-bar')).toHaveCount(0);
  await expect(page.locator('.spot.proposed')).toHaveCount(0);
  await page.getByRole('button', { name: 'People', exact: true }).click();
  const cells = page.locator('.heat-cell');
  await expect(cells).toHaveCount(42);
  await page
    .locator('tr')
    .filter({ hasText: 'Ilya Sukhanov' })
    .locator('.heat-cell')
    .first()
    .click();
  await expect(page.locator('.people-detail')).toContainText('Ilya Sukhanov');
  await expect(page.locator('.people-detail')).toContainText('free 6 AM–6 PM');
  await page.screenshot({ path: 'test-results/v2-people.png', fullPage: true });
});
