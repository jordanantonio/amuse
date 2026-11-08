import { expect, test } from '@playwright/test';
import { navLink, signInAs } from './helpers';

test.beforeEach(async ({ request, page }) => {
  expect((await request.post('/api/v1/dev/reset')).ok()).toBeTruthy();
  page.on('dialog', (d) => void d.accept());
});

test('Maya’s For You feed: eligible only, why, greyed reasons, one-tap apply', async ({ page }) => {
  await signInAs(page, 'u-maya');
  await expect(
    page.getByRole('heading', { name: /3 new contracts fit you since yesterday/ }),
  ).toBeVisible();
  await expect(page.getByRole('link', { name: /1 offer is waiting for your reply/ })).toBeVisible();
  const cards = page.locator('.feed-list .contract-card');
  await expect(cards).toHaveCount(10);
  await expect(cards.first()).toContainText('You have');
  await cards.first().getByRole('button', { name: 'Why am I seeing this?' }).click();
  await expect(page.getByRole('dialog', { name: 'Why you’re seeing this' })).toContainText(
    'You hold 3 of 3 required certs',
  );
  await page.keyboard.press('Escape');
  await page.screenshot({ path: 'test-results/v1-home-worker.png', fullPage: true });

  await page.getByLabel('Only show ones I qualify for').uncheck();
  const greyed = page.locator('.contract-card.ineligible').filter({ hasText: 'Site labourer' });
  await expect(greyed).toContainText('Missing: Fall Protection');
  await page.getByLabel('Only show ones I qualify for').check();

  const panel = cards.filter({ hasText: 'Shop electrician, panel builds' });
  await panel.getByRole('button', { name: 'Apply' }).click();
  const sheet = page.getByRole('dialog', { name: /Apply to Shop electrician/ });
  for (let i = 0; i < 3; i++) await sheet.getByRole('button', { name: 'Continue' }).click();
  await sheet.getByRole('button', { name: 'Send application' }).click();
  await sheet.getByRole('button', { name: 'Close' }).click();
  await expect(panel.getByRole('link', { name: 'Applied, see Work' })).toBeVisible();
  await navLink(page, 'Work').click();
  await page.getByRole('tab', { name: /Applied/ }).click();
  await expect(page.locator('.work-list')).toContainText('Shop electrician, panel builds');
});

test('posting page shows the eligibility box and hides the site until an offer', async ({
  page,
}) => {
  await signInAs(page, 'u-maya');
  await page.goto('/postings/p-site-labour');
  const box = page.locator('.eligibility');
  await expect(box.locator('.elig-row.missing')).toContainText('Fall Protection');
  await expect(box.locator('.elig-row.ok')).toContainText('CSTS-2020');
  await expect(page.getByText('The site address is shared once you get an offer.')).toBeVisible();
  await page.goto('/postings/p-high-bay');
  await expect(page.locator('.elig-row.pending')).toContainText('Aerial work platform');
});

test('Northline reviews three applicants, sends an offer, and posts a contract', async ({
  page,
  browser,
}) => {
  await signInAs(page, 'u-alex');
  await expect(page.getByRole('link', { name: /new applicants/ })).toBeVisible();
  await navLink(page, 'Work').click();
  await page.getByRole('button', { name: 'Review applicants' }).first().click();
  await page.getByLabel('Posting').selectOption({ label: 'Finish carpenter, show homes (3)' });
  const rows = page.locator('.applicant-row');
  await expect(rows).toHaveCount(3);
  const ella = rows.filter({ hasText: 'Ella Thompson' });
  await expect(ella).toContainText('2 of 2 required certs');
  await ella.getByRole('button', { name: 'Send offer' }).click();
  await expect(ella).toContainText('Offer waiting');
  await page.screenshot({ path: 'test-results/v1-work-business.png', fullPage: true });

  await page.getByRole('tab', { name: 'Postings' }).click();
  await page.getByRole('button', { name: 'New posting' }).click();
  const form = page.getByRole('dialog', { name: 'New posting' });
  await form.getByLabel('Trade').selectOption('Plumbing');
  await expect(form.getByLabel('Description')).toHaveValue(/plumber/);
  await form.getByLabel('Title').fill('Plumber, 6 townhomes');
  await form.getByLabel('City').selectOption('Edmonton');
  await form.getByLabel('Pay (CAD)').fill('45');
  await form
    .locator('.req')
    .filter({ hasText: 'CSTS-2020' })
    .getByRole('button', { name: 'Required' })
    .click();
  await form.getByRole('button', { name: 'Publish posting' }).click();
  await expect(form).toHaveCount(0);
  await expect(page.locator('.work-list')).toContainText('Plumber, 6 townhomes');

  // Ella sees the offer with the site address revealed.
  const ellaPage = await (await browser.newContext()).newPage();
  await signInAs(ellaPage, 'u-ella');
  await ellaPage.goto('/work?tab=offers');
  await expect(ellaPage.locator('.offer-card')).toContainText('4210 Allard Way SW, Edmonton');
});
