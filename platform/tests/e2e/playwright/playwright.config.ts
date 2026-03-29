import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for E2E tests
 * 
 * Run with: npx playwright test
 * Debug with: npx playwright test --debug
 * UI mode: npx playwright test --ui
 */
export default defineConfig({
  testDir: './tests',
  
  /* Run tests in files in parallel */
  fullyParallel: true,
  
  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,
  
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  
  /* Use single worker to avoid overwhelming the server */
  workers: 1,
  
  /* Reporter to use */
  reporter: [
    ['html', { open: 'never' }],
    ['list']
  ],
  
  /* Shared settings for all the projects below */
  use: {
    /* Base URL to use in actions like `await page.goto('/')` */
    baseURL: process.env.FRONTEND_URL || 'http://localhost:3000',
    
    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',
    
    /* Capture screenshot on failure */
    screenshot: 'only-on-failure',
    
    /* Record video on failure */
    video: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Timeout settings */
  timeout: 60000,
  expect: {
    timeout: 15000,
  },
  
  /* Navigation timeout */
  navigationTimeout: 30000,

  /* Run your local dev server before starting the tests */
  // Uncomment if you want Playwright to start the frontend
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  //   cwd: '../../../dashboard/frontend',
  // },
});
