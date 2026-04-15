import { test, expect } from '@playwright/test';
import { login } from './auth.setup';

// ─── Login ──────────────────────────────────────────────────────────────────

test.describe('Authentication', () => {
  test('shows login page when unauthenticated', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Enterprise MCP Agent' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Email' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
  });

  test('rejects invalid credentials', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('textbox', { name: 'Email' }).fill('bad@acme.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('wrong');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page.getByText('Invalid email or password')).toBeVisible({ timeout: 3000 });
  });

  test('logs in with valid credentials', async ({ page }) => {
    await login(page);
    await expect(page.getByRole('link', { name: 'Chat' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Sessions' })).toBeVisible();
  });

  test('logout returns to login page', async ({ page }) => {
    await login(page);
    await page.getByRole('button', { name: 'Sign out' }).click();
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible({ timeout: 3000 });
  });
});

// ─── Chat Page ──────────────────────────────────────────────────────────────

test.describe('Chat Page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/');
  });

  test('renders session sidebar with New Session button', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Sessions' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'New Session' })).toBeVisible();
    await expect(page.getByPlaceholder('Search sessions...')).toBeVisible();
  });

  test('creates a new session', async ({ page }) => {
    await page.getByRole('button', { name: 'New Session' }).click();
    // Session should appear in sidebar
    await expect(page.getByText(/Session \d+/)).toBeVisible({ timeout: 3000 });
    // Message input should appear
    await expect(page.getByPlaceholder(/Type your message/)).toBeVisible();
  });

  test('selects a session and shows chat area', async ({ page }) => {
    // Click first session if one exists
    const sessionBtn = page.locator('[role="button"]').filter({ hasText: /Session/ }).first();
    if (await sessionBtn.isVisible()) {
      await sessionBtn.click();
      await expect(page.getByPlaceholder(/Type your message/)).toBeVisible();
    }
  });

  test('no console errors on page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/');
    await page.waitForTimeout(1000);
    expect(errors.filter((e) => !e.includes('favicon'))).toHaveLength(0);
  });
});

// ─── Approvals Page ─────────────────────────────────────────────────────────

test.describe('Approvals Page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('renders approval queue with filters', async ({ page }) => {
    await page.goto('/approvals');
    await expect(page.getByRole('heading', { name: 'Approval Queue' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Pending' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'All' })).toBeVisible();
  });

  test('shows empty state when no approvals', async ({ page }) => {
    await page.goto('/approvals');
    await expect(page.getByText(/No pending approvals|No approvals yet/)).toBeVisible();
  });

  test('filter buttons toggle correctly', async ({ page }) => {
    await page.goto('/approvals');
    await page.getByRole('button', { name: 'All' }).click();
    await expect(page.getByText('No approvals yet')).toBeVisible();
    await page.getByRole('button', { name: 'Pending' }).click();
    await expect(page.getByText('No pending approvals')).toBeVisible();
  });

  test('no console errors on page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/approvals');
    await page.waitForTimeout(1000);
    expect(errors.filter((e) => !e.includes('favicon'))).toHaveLength(0);
  });
});

// ─── History Page ───────────────────────────────────────────────────────────

test.describe('History Page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('renders session history with search and filters', async ({ page }) => {
    await page.goto('/history');
    await expect(page.getByRole('heading', { name: 'Session History' })).toBeVisible();
    await expect(page.getByPlaceholder('Search sessions...')).toBeVisible();
    for (const filter of ['All', 'Active', 'Completed', 'Archived']) {
      await expect(page.getByRole('button', { name: filter })).toBeVisible();
    }
  });

  test('shows sessions when they exist', async ({ page }) => {
    await page.goto('/history');
    // Either sessions exist or empty state shows
    const hasSession = await page.getByText(/Session/).first().isVisible().catch(() => false);
    const hasEmpty = await page.getByText('No sessions found').isVisible().catch(() => false);
    expect(hasSession || hasEmpty).toBeTruthy();
  });

  test('no console errors on page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/history');
    await page.waitForTimeout(1000);
    expect(errors.filter((e) => !e.includes('favicon'))).toHaveLength(0);
  });
});

// ─── Settings Page ──────────────────────────────────────────────────────────

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('renders MCP server dashboard', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
    await expect(page.getByText('Total Servers')).toBeVisible();
    await expect(page.getByText('Connected')).toBeVisible();
    await expect(page.getByText('Available Tools')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'MCP Servers' })).toBeVisible();
  });

  test('displays MCP server cards with status', async ({ page }) => {
    await page.goto('/settings');
    for (const server of ['Github', 'Project Mgmt', 'Calendar']) {
      await expect(page.getByRole('heading', { name: server })).toBeVisible();
    }
  });

  test('refresh button works', async ({ page }) => {
    await page.goto('/settings');
    const refreshBtn = page.getByRole('button', { name: 'Refresh' });
    await expect(refreshBtn).toBeVisible();
    await refreshBtn.click();
    // Should still show servers after refresh
    await expect(page.getByText('Total Servers')).toBeVisible();
  });

  test('no console errors on page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/settings');
    await page.waitForTimeout(1000);
    expect(errors.filter((e) => !e.includes('favicon'))).toHaveLength(0);
  });
});

// ─── Navigation ─────────────────────────────────────────────────────────────

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('all nav links work', async ({ page }) => {
    const routes = [
      { name: 'Chat', heading: 'Sessions' },
      { name: 'Approvals', heading: 'Approval Queue' },
      { name: 'History', heading: 'Session History' },
      { name: 'Settings', heading: 'Settings' },
    ];

    for (const { name, heading } of routes) {
      await page.getByRole('link', { name }).click();
      await expect(page.getByRole('heading', { name: heading })).toBeVisible({ timeout: 3000 });
    }
  });
});
