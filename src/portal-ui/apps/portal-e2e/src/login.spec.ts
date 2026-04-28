import { test, expect } from '@playwright/test';

// NOTE: These tests assume a running Keycloak with test user orbit-test/Test@1234
// Configure via ORBIT_USER / ORBIT_PASS env vars in CI.

const USER = process.env['ORBIT_USER'] ?? 'orbit-test';
const PASS = process.env['ORBIT_PASS'] ?? 'Test@1234';

test.describe('Portal login and navigation', () => {
  test('redirects unauthenticated users to Keycloak', async ({ page }) => {
    await page.goto('/projects');
    await expect(page).toHaveURL(/auth\.ai\.adports\.ae/);
  });

  test('logs in and shows Projects page', async ({ page }) => {
    await page.goto('/projects');
    // Fill Keycloak login form
    await page.fill('#username', USER);
    await page.fill('#password', PASS);
    await page.click('#kc-login');

    await expect(page).toHaveURL(/\/projects/);
    await expect(page.locator('h1')).toContainText('Projects');
  });

  test('ledger page accessible after login', async ({ page }) => {
    await page.goto('/projects');
    await page.fill('#username', USER);
    await page.fill('#password', PASS);
    await page.click('#kc-login');

    await page.click('text=Ledger');
    await expect(page.locator('h1')).toContainText('Ledger Explorer');
  });
});
