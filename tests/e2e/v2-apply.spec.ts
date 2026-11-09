import { expect, test } from '@playwright/test';
import { signInAs } from './helpers';

test.beforeEach(async ({ request }) => {
  expect((await request.post('/api/v1/dev/reset')).ok()).toBeTruthy();
});

test('Ilya: Why panel, then the 4-step apply flow for the sanitation crew', async ({ page }) => {
  await signInAs(page, 'u-ilya');
  const card = page
    .locator('.feed-list .contract-card')
    .filter({ hasText: 'General Labourer — Sanitation Crew' });
  await card.getByRole('button', { name: 'Why am I seeing this?' }).click();
  const why = page.getByRole('dialog', { name: 'Why you’re seeing this' });
  await expect(why).toContainText('9 km from you, well inside your 25 km radius');
  await expect(why).toContainText('You hold 3 of 3 required certs');
  await expect(why).toContainText('You also hold Forklift operator, which this employer values.');
  await expect(why).toContainText('Pays $26/h, above your $24/h minimum.');
  await expect(why).toContainText('Fits your calendar with no conflicts.');
  await expect(why).toContainText('Posted today');
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'test-results/v2-why.png' });
  await why.getByRole('button', { name: 'Apply' }).click();

  const sheet = page.getByRole('dialog', { name: /Apply to General Labourer/ });
  await expect(sheet).toContainText('Step 1 of 4');
  await expect(sheet).toContainText('A typical day');
  await expect(sheet).toContainText('CSA steel-toe rubber boots');
  await sheet.getByRole('button', { name: 'Continue' }).click();
  await expect(sheet).toContainText('No conflicts with your schedule');
  await sheet.getByRole('button', { name: 'Continue' }).click();
  await sheet
    .getByRole('group', { name: 'Comfortable with overnight shifts?' })
    .getByText('Yes')
    .click();
  await sheet
    .getByRole('group', { name: 'Do you have CSA steel-toe boots?' })
    .getByText('Yes')
    .click();
  await sheet.getByLabel('Earliest start date').fill('2026-11-25');
  await sheet.getByRole('button', { name: 'Continue' }).click();
  await expect(sheet).toContainText('Review and send');
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'test-results/v2-apply-review.png' });
  await sheet.getByRole('button', { name: 'Send application' }).click();
  await expect(sheet.locator('.mini-timeline li.done')).toHaveText('Applied');
  await sheet.getByRole('link', { name: 'Track it in Work' }).click();
  await expect(page.locator('.work-list')).toContainText('General Labourer — Sanitation Crew');
});

test('Schedule links to Google Calendar without OAuth', async ({ page }) => {
  await signInAs(page, 'u-ilya');
  await page.goto('/schedule');
  const open = page.getByRole('link', { name: 'Open in Google Calendar' });
  await expect(open).toHaveAttribute(
    'href',
    /^https:\/\/calendar\.google\.com\/calendar\/r\/week\/\d{4}\/\d{2}\/\d{2}$/,
  );
});
