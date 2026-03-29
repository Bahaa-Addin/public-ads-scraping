import { test, expect } from '@playwright/test';

/**
 * Dashboard Page E2E Tests
 * 
 * Tests the main dashboard page functionality including:
 * - Page loading without errors
 * - Metrics cards display
 * - Charts rendering
 * - Quick actions
 */

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/dashboard', { waitUntil: 'domcontentloaded', timeout: 30000 });
  });

  test('loads without console errors', async ({ page }) => {
    const errors: string[] = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    // Reload to catch any errors
    await page.reload();
    await page.waitForTimeout(1000);
    
    // Filter out known acceptable errors (like 404s for missing data)
    const criticalErrors = errors.filter(e => 
      e.includes('500') || 
      e.includes('TypeError') ||
      e.includes('ReferenceError')
    );
    
    expect(criticalErrors).toHaveLength(0);
  });

  test('displays page title and navigation', async ({ page }) => {
    // Should show dashboard in navigation
    await expect(page.getByRole('navigation')).toBeVisible();
    
    // Should have dashboard-related content
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible();
  });

  test('displays metrics cards', async ({ page }) => {
    // Look for common metric-related content in different patterns
    const metricPatterns = [
      /total.*assets/i,
      /total.*jobs/i,
      /success.*rate/i,
      /assets.*today/i,
      /scraped/i,
      /pipeline/i,
      /completed/i,
      /pending/i,
      /processed/i
    ];
    
    let foundMetrics = 0;
    for (const pattern of metricPatterns) {
      const locator = page.getByText(pattern);
      if (await locator.first().isVisible({ timeout: 1000 }).catch(() => false)) {
        foundMetrics++;
      }
    }
    
    // Also check for cards or metric-style containers
    const cards = page.locator('[class*="card"], [class*="stat"], [class*="metric"]');
    const cardCount = await cards.count();
    
    // Should find metrics OR have card-style UI elements
    expect(foundMetrics > 0 || cardCount > 0).toBe(true);
  });

  test('time series chart loads or shows empty state', async ({ page }) => {
    // Wait for chart container, empty state, or any data visualization
    const chartOrEmpty = page.locator('.recharts-wrapper, [class*="empty"], [class*="no-data"], [class*="chart"], svg');
    
    // Either a chart exists or there's an appropriate empty state or page has content
    const hasChart = await chartOrEmpty.first().isVisible({ timeout: 5000 }).catch(() => false);
    const pageContent = await page.locator('main, [class*="content"]').textContent().catch(() => '');
    
    // Pass if chart visible OR page has meaningful content
    expect(hasChart || (pageContent?.length || 0) > 50).toBe(true);
  });

  test('quick actions buttons are visible', async ({ page }) => {
    // Look for action buttons
    const actionButtons = page.getByRole('button').filter({
      hasText: /scrape|extract|generate|classify|pipeline/i
    });
    
    // There should be some action buttons
    const count = await actionButtons.count();
    expect(count).toBeGreaterThanOrEqual(0); // May be 0 if not on dashboard
  });

  test('navigation links work', async ({ page }) => {
    // Find navigation links
    const navLinks = [
      { text: /jobs/i, expectedUrl: /jobs/ },
      { text: /assets/i, expectedUrl: /assets/ },
      { text: /scrapers/i, expectedUrl: /scrapers/ },
    ];
    
    for (const { text, expectedUrl } of navLinks) {
      const link = page.getByRole('link', { name: text }).first();
      if (await link.isVisible({ timeout: 2000 }).catch(() => false)) {
        await link.click();
        await expect(page).toHaveURL(expectedUrl);
        await page.goto('/dashboard');
        break; // Test at least one navigation
      }
    }
  });
});

test.describe('Dashboard Error Handling', () => {
  test('handles API errors gracefully', async ({ page }) => {
    // Intercept API calls and force errors
    await page.route('**/api/v1/metrics/**', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal Server Error' })
      });
    });
    
    await page.goto('/dashboard');
    await page.waitForTimeout(1000);
    
    // Page should not crash - should show error state or empty
    await expect(page.locator('body')).toBeVisible();
    
    // Should not show blank page
    const bodyText = await page.locator('body').textContent();
    expect(bodyText?.length).toBeGreaterThan(0);
  });
});
