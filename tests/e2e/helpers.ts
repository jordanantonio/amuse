import { expect, type Page } from '@playwright/test';

export async function signInAs(page: Page, name: RegExp) {
  await page.goto('/signin/demo');
  await page.getByRole('button', { name }).click();
  await expect(page).toHaveURL(/\/home$/);
}

/** Main navigation link; the Work tab's name includes its waiting-count badge. */
export const navLink = (page: Page, label: string) =>
  page.locator('.v1-nav').getByRole('link', { name: new RegExp(`^${label}`) });
