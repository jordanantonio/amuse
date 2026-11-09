import { expect, test } from '@playwright/test';
import { signInAs } from './helpers';

test.beforeEach(async ({ request, page }) => {
  expect((await request.post('/api/v1/dev/reset')).ok()).toBeTruthy();
  page.on('dialog', (d) => void d.accept());
});

test('Rahul ranks warehouse applicants with coverage, flags and the requirements pile', async ({
  page,
}) => {
  await signInAs(page, 'u-rahul');
  await page.goto('/work?tab=applicants&posting=p-warehouse');
  const strip = page.locator('.coverage-strip');
  await expect(strip).toContainText('Forklift operator: need 2, hired 1');
  await expect(strip).toContainText('Standard First Aid & CPR: need 1, covered');
  const rows = page.locator('.work-list').first().locator('.applicant-row');
  await expect(rows.first()).toContainText('Ilya Sukhanov');
  await expect(rows.first()).toContainText('Fills a gap: Forklift operator');
  await expect(rows.first()).toContainText('Forklift operator · Valuable');
  await expect(rows.last()).toContainText('Tyler Brandt');
  await expect(rows.last()).toContainText('Possible auto-apply');
  await rows
    .first()
    .getByRole('button', { name: /Fit score/ })
    .click();
  await expect(rows.first().locator('.fit-rows')).toContainText('Holds 1 of 1 required certs');
  await expect(page.getByLabel('Auto-decline applicants missing required certs')).not.toBeChecked();
  await page.screenshot({ path: 'test-results/v2-rank.png', fullPage: true });

  const pile = page.locator('details.pile');
  await expect(pile).toContainText('Doesn’t meet requirements (2)');
  await pile.locator('summary').click();
  await expect(pile).toContainText('Missing WHMIS');
  await pile.getByRole('button', { name: 'Decline all with a polite message' }).click();
  await expect(page.locator('details.pile')).toHaveCount(0);
});
