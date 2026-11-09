import { expect, type Page } from '@playwright/test';

const NAMES: Record<string, string> = {
  'u-maya': 'u-maya',
  'u-alex': 'u-alex',
  'u-ella': 'u-ella',
  'u-priya': 'u-priya',
  'u-ilya': 'u-ilya',
  'u-rahul': 'u-rahul',
  'u-jordan': 'u-jordan',
};

/** Sign in as any seeded demo account (the picker itself only shows three personas). */
export async function signInAs(page: Page, userId: keyof typeof NAMES) {
  const r = await page.request.post('/api/v1/auth/demo', { data: { user_id: NAMES[userId] } });
  expect(r.ok()).toBeTruthy();
  await page.goto('/home');
  await expect(page).toHaveURL(/\/home$/);
}

/** Main navigation link; the Work tab's name includes its waiting-count badge. */
export const navLink = (page: Page, label: string) =>
  page.locator('.v1-nav').getByRole('link', { name: new RegExp(`^${label}`) });
