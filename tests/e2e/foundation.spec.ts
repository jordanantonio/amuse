import { test, expect } from '@playwright/test';

test.beforeEach(async ({ request }) => {
  const response = await request.post('http://127.0.0.1:8000/api/v1/demo/reset', {
    headers: { 'X-Demo-Persona': 'demo-admin' },
  });
  expect(response.ok()).toBeTruthy();
});

test('manager dashboard → explicit disruption → real CP-SAT proposal', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Good morning, Alex.' })).toBeVisible();
  await expect(page.getByText('FICTIONAL DEMO')).toBeVisible();
  await page.screenshot({ path: 'test-results/shift-desktop.png', fullPage: true });
  await page.getByRole('button', { name: 'Team calendar', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Every project. Everyone in view.' }),
  ).toBeVisible();
  await expect(page.locator('body')).not.toContainText('health appointment');
  await page.getByRole('button', { name: 'Schedule lab', exact: false }).first().click();
  await page
    .locator('.current-assignment')
    .filter({ hasText: 'Maya Brooks' })
    .getByRole('button', { name: 'Record absence' })
    .click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Record absence', exact: true })
    .click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button', { name: 'Generate draft schedule' }).click();
  await expect(page.getByRole('heading', { name: 'Your proposed schedule' })).toBeVisible();
  await expect(page.locator('.draft-panel')).toContainText('Sofia Rivera');
  await expect(page.locator('.draft-panel')).toContainText('Proposed');
  await expect(page.locator('.draft-panel')).toContainText('OPTIMAL');
  await expect(page.locator('.draft-panel')).toContainText('does not reserve time');
  await page.screenshot({ path: 'test-results/shift-solver.png', fullPage: true });
  await page.getByRole('button', { name: 'Team calendar', exact: true }).click();
  // A proposal must not appear as a confirmed electrical assignment for Sofia.
  const sofia = page.locator('tr').filter({ hasText: 'Sofia Rivera' });
  await expect(sofia.locator('.calendar-event')).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('worker privacy, live marketplace search, and mobile layout', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Good morning, Alex.' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ path: 'test-results/shift-mobile.png', fullPage: true });
  await page.getByLabel('Demo persona').selectOption('demo-sofia');
  await expect(page.getByRole('heading', { name: 'Good morning, Sofia.' })).toBeVisible();
  await page.getByRole('button', { name: 'Toggle menu' }).click();
  await page.getByRole('button', { name: 'My schedule', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Make room for great work.' })).toBeVisible();
  await expect(page.locator('.team-calendar tbody tr')).toHaveCount(1);
  await expect(page.locator('body')).not.toContainText('PRIVATE:');
  await page.getByRole('button', { name: 'Toggle menu' }).click();
  await page.getByRole('button', { name: 'Talent marketplace', exact: true }).click();
  await page.getByRole('textbox', { name: 'Search marketplace' }).fill('welder');
  await expect(page.locator('.job-card')).toHaveCount(1);
  await expect(page.locator('.job-card')).toContainText('Structural welder');
});
