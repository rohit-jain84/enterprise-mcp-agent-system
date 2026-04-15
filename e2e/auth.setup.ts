import { test, expect } from '@playwright/test';

const EMAIL = process.env.TEST_EMAIL || 'admin@acme.com';
const PASSWORD = process.env.TEST_PASSWORD || 'admin123';

/**
 * Authenticate and store the JWT in localStorage so subsequent tests skip login.
 * Call this once before the test suite, or at the start of each test file.
 */
export async function login(page: import('@playwright/test').Page) {
  await page.goto('/');

  // If already authenticated (token in localStorage), skip login
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  if (token) return;

  await page.getByRole('textbox', { name: 'Email' }).fill(EMAIL);
  await page.getByRole('textbox', { name: 'Password' }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign In' }).click();

  // Wait for the main layout to appear (nav with Chat link)
  await expect(page.getByRole('link', { name: 'Chat' })).toBeVisible({ timeout: 5000 });
}
