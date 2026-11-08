import { expect, test } from '@playwright/test';
import { navLink, signInAs } from './helpers';

test.beforeEach(async ({ request, page }) => {
  expect((await request.post('/api/v1/dev/reset')).ok()).toBeTruthy();
  page.on('dialog', (d) => void d.accept());
});

test('accept an offer: withdraw overlaps, block dates, calendar, schedule', async ({
  page,
  browser,
}) => {
  await signInAs(page, 'u-maya');
  await page.goto('/work?tab=offers');
  const offer = page
    .locator('.offer-card')
    .filter({ hasText: 'Maintenance electrician, night shift' });
  await expect(offer).toContainText('6505 Sparrow Dr, Leduc');
  await offer.getByRole('button', { name: 'Accept offer' }).click();

  const dialog = page.getByRole('dialog', { name: 'Accept this offer?' });
  await expect(dialog).toContainText('every day from start to end will be blocked');
  const overlap = dialog.getByLabel(/Packaging line lead, weekends/);
  await expect(overlap).toBeChecked();
  await dialog.getByRole('button', { name: 'Accept and block dates' }).click();

  const done = page.getByRole('dialog', { name: 'You’re booked' });
  await expect(done).toContainText(
    'Maintenance electrician, night shift with Prairie Harvest Foods',
  );
  await expect(done.getByRole('link', { name: 'Add to Google Calendar' })).toHaveAttribute(
    'href',
    /calendar\.google\.com\/calendar\/render\?action=TEMPLATE&text=Shift.*&dates=\d{8}%2F\d{8}/,
  );
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    done.getByRole('link', { name: 'Download .ics' }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/^shift-maintenance-electrician.*\.ics$/);
  await done.getByRole('button', { name: 'Done' }).click();

  await page.getByRole('tab', { name: 'Active' }).click();
  await expect(page.locator('.work-list')).toContainText('Maintenance electrician, night shift');
  await page.getByRole('tab', { name: 'Past' }).click();
  await expect(page.locator('.work-list')).toContainText('Packaging line lead, weekends');

  // The booked dates now gate the feed.
  await navLink(page, 'Home').click();
  await expect(page.locator('.feed-list')).not.toContainText('Electrical rough-in, 4-plex');

  await navLink(page, 'Schedule').click();
  await expect(page.locator('.agenda')).toContainText('Maintenance electrician, night shift');
  await page.getByRole('button', { name: 'Mark unavailable' }).click();
  const block = page.getByRole('dialog', { name: 'Mark yourself unavailable' });
  await block.getByLabel(/Reason/).fill('Family trip');
  await block.getByRole('button', { name: 'Save' }).click();
  await expect(page.locator('.agenda')).toContainText('Family trip');
  await page.screenshot({ path: 'test-results/v1-schedule-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ path: 'test-results/v1-schedule-mobile.png', fullPage: true });

  // The business sees its new crew member on its schedule.
  const priya = await (await browser.newContext()).newPage();
  await signInAs(priya, 'u-priya');
  await priya.goto('/schedule');
  await expect(priya.locator('.agenda')).toContainText('Maya Brooks');
});
