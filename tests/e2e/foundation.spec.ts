import { test, expect } from '@playwright/test';

test.beforeEach(async ({ request }) => {
  const response = await request.post('http://127.0.0.1:8000/api/v1/demo/reset', {
    headers: { 'X-Demo-Persona': 'demo-admin' },
  });
  expect(response.ok()).toBeTruthy();
});

test('weather and absence recovery → manager approval → worker acceptance → published calendars', async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/dev/legacy-planner');
  await expect(page.getByRole('heading', { name: 'Week of November 9' })).toBeVisible();
  await page.screenshot({ path: 'test-results/shift-adaptive-overview.png', fullPage: true });
  await page.getByRole('link', { name: 'SHIFT Adaptive', exact: true }).click();
  await page.getByRole('button', { name: 'Simulate heavy rain', exact: true }).click();
  await expect(page.getByRole('heading', { name: /Review: .* risks identified/ })).toBeVisible();
  await expect(page.locator('.risk-panel')).toContainText('rain probability');
  await page
    .locator('.current-assignment')
    .filter({ hasText: 'Maya Brooks' })
    .getByRole('button', { name: 'Record absence' })
    .click();
  await page.getByLabel('Unavailable until').fill('2026-11-13T17:00');
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button', { name: 'Generate recovery options' }).click();
  await expect(page.locator('.alternative-card')).toHaveCount(3);
  await expect(page.getByRole('heading', { name: 'Original confirmed plan' })).toBeVisible();
  await expect(page.locator('#proposal-comparison')).toContainText('Sofia Rivera');
  await page.screenshot({ path: 'test-results/shift-adaptive-comparison.png', fullPage: true });
  const proposalId = new URL(page.url()).searchParams.get('proposal')!;
  await page.getByRole('button', { name: 'Approve & request acceptance' }).click();
  await expect(page.locator('.confirmation-list')).toBeVisible();
  const response = await request.get(`http://127.0.0.1:8000/api/v1/proposals/${proposalId}`);
  const proposal = await response.json();
  // No original assignment has been cancelled at approval.
  let dashboard = await (await request.get('http://127.0.0.1:8000/api/v1/dashboard')).json();
  expect(dashboard.assignments.find((a: { id: string }) => a.id === 'assignment-maya').status).toBe(
    'confirmed',
  );
  for (const c of proposal.confirmations) {
    await page.getByLabel('Demo persona').selectOption('demo-' + c.worker_id);
    await page.goto(`/dev/legacy-planner?view=inbox&project=eastside&proposal=${proposalId}`);
    await expect(
      page.getByRole('button', { name: 'Accept assignments', exact: true }),
    ).toBeVisible();
    await page.getByRole('button', { name: 'Accept assignments', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Accept assignments', exact: true })).toHaveCount(
      0,
    );
  }
  await page.getByLabel('Demo persona').selectOption('demo-manager');
  await page.goto(`/dev/legacy-planner?view=inbox&project=eastside&proposal=${proposalId}`);
  await page.getByRole('button', { name: 'Revalidate & publish schedule' }).click();
  await expect(page.locator('#proposal-comparison > .section-heading')).toContainText('Published');
  dashboard = await (await request.get('http://127.0.0.1:8000/api/v1/dashboard')).json();
  expect(dashboard.assignments.find((a: { id: string }) => a.id === 'assignment-maya').status).toBe(
    'cancelled',
  );
  expect(dashboard.assignments.find((a: { id: string }) => a.id === 'assignment-noah').status).toBe(
    'confirmed',
  );
  await page.getByRole('link', { name: 'Team calendar', exact: true }).click();
  await expect(
    page.locator('tr').filter({ hasText: 'Sofia Rivera' }).locator('.confirmed-event'),
  ).not.toHaveCount(0);
  await expect(page.locator('body')).not.toContainText('PRIVATE:');
  expect(errors).toEqual([]);
});

test('worker mobile profile, availability, application and calendar date navigation', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/dev/legacy-planner');
  await expect(page.getByRole('heading', { name: 'Week of November 9' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ path: 'test-results/shift-adaptive-mobile.png', fullPage: true });
  await page.getByLabel('Demo persona').selectOption('demo-sofia');
  await expect(page.getByRole('heading', { name: 'Your week, Sofia' })).toBeVisible();
  await page.getByRole('button', { name: 'Toggle menu' }).click();
  await page.getByRole('link', { name: 'Marketplace', exact: true }).click();
  await page.getByRole('textbox', { name: 'Search marketplace' }).fill('electrician');
  await page.getByRole('button', { name: 'Apply for role' }).click();
  await expect(page.getByRole('button', { name: 'Applied', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Toggle menu' }).click();
  await page.getByRole('link', { name: 'My profile', exact: true }).click();
  await page.getByRole('button', { name: 'Edit profile', exact: true }).click();
  await page.getByLabel('Professional title').fill('Independent electrical specialist');
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page.locator('.profile-overview')).toContainText(
    'Independent electrical specialist',
  );
  await page.getByRole('button', { name: 'Edit availability', exact: true }).click();
  await page.getByLabel('Available windows').fill('2026-11-09 12:00 / 2026-11-09 17:00');
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button', { name: 'Toggle menu' }).click();
  await page.getByRole('link', { name: 'My schedule', exact: true }).click();
  await expect(page.locator('.team-calendar tbody tr')).toHaveCount(1);
  await page.getByRole('button', { name: 'Next period' }).click();
  await expect(page.locator('.free-window')).toHaveCount(0);
  await page.getByRole('button', { name: 'Demo week', exact: true }).click();
  await expect(page.locator('.free-window')).not.toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});

test('project and task editors persist new scope and URLs survive reload', async ({ page }) => {
  await page.goto('/dev/legacy-planner?view=projects&project=eastside');
  await expect(page.getByRole('heading', { name: 'Turn scope into a shared plan.' })).toBeVisible();
  await page.getByRole('button', { name: 'New project', exact: true }).click();
  await page.getByLabel('Project name', { exact: true }).fill('Browser-verified fabrication');
  await page.getByLabel('Client / company').fill('Demo client');
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.locator('.project-detail h2')).toHaveText('Browser-verified fabrication');
  await page.getByRole('button', { name: 'Add task', exact: true }).click();
  await page.getByLabel('Task name', { exact: true }).fill('Electrical inspection');
  await page.getByLabel('Required skills (comma separated)').fill('Electrical');
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page.locator('.task-row')).toContainText('Electrical inspection');
  const url = page.url();
  await page.reload();
  await expect(page.locator('.project-detail h2')).toHaveText('Browser-verified fabrication');
  expect(page.url()).toBe(url);
});
