/**
 * Low-RAM Safety Limits for Scrapers
 * 
 * These limits ensure the scraping system can run on machines with limited resources.
 * All scrapers MUST respect these limits.
 * 
 * Environment Variables:
 * - MAX_BROWSER_INSTANCES: Maximum concurrent browser instances (default: 1)
 * - BROWSER_HEADLESS: Run in headless mode (default: true)
 * - SEQUENTIAL_SCRAPING: Force sequential scraping (default: true)
 * - MAX_CONCURRENT_SCRAPES: Maximum concurrent scrape jobs (default: 1)
 * - IMAGE_ONLY_MODE: Only process images, skip video (default: true)
 * - MAX_IMAGE_DIMENSION: Max image dimension before downscaling (default: 1920)
 * - VIDEO_FRAME_SAMPLE_LIMIT: Max frames to sample from video (default: 10)
 * - GLOBAL_JOB_CAP: Maximum total jobs to process (default: 100)
 * - MAX_QUEUE_SIZE: Maximum queue size (default: 1000)
 * - REQUEST_DELAY_MS: Delay between requests in ms (default: 1000)
 */

import dotenv from 'dotenv';

dotenv.config();

/**
 * Get environment variable with default value
 */
function getEnvInt(name, defaultValue) {
  const value = process.env[name];
  return value ? parseInt(value, 10) : defaultValue;
}

function getEnvBool(name, defaultValue) {
  const value = process.env[name];
  if (value === undefined) return defaultValue;
  return value.toLowerCase() === 'true';
}

/**
 * Resource limits configuration
 */
export const LIMITS = {
  // Browser limits
  MAX_BROWSER_INSTANCES: getEnvInt('MAX_BROWSER_INSTANCES', 1),
  BROWSER_HEADLESS: getEnvBool('BROWSER_HEADLESS', true),
  
  // Concurrency limits
  SEQUENTIAL_SCRAPING: getEnvBool('SEQUENTIAL_SCRAPING', true),
  MAX_CONCURRENT_SCRAPES: getEnvInt('MAX_CONCURRENT_SCRAPES', 1),
  MAX_CONCURRENT_DOWNLOADS: getEnvInt('MAX_CONCURRENT_DOWNLOADS', 3),
  
  // Asset processing limits
  IMAGE_ONLY_MODE: getEnvBool('IMAGE_ONLY_MODE', true),
  MAX_IMAGE_DIMENSION: getEnvInt('MAX_IMAGE_DIMENSION', 1920),
  MAX_IMAGE_SIZE_BYTES: getEnvInt('MAX_IMAGE_SIZE_BYTES', 10 * 1024 * 1024), // 10MB
  VIDEO_FRAME_SAMPLE_LIMIT: getEnvInt('VIDEO_FRAME_SAMPLE_LIMIT', 10),
  
  // Job limits
  GLOBAL_JOB_CAP: getEnvInt('GLOBAL_JOB_CAP', 100),
  MAX_QUEUE_SIZE: getEnvInt('MAX_QUEUE_SIZE', 1000),
  MAX_ITEMS_PER_SCRAPE: getEnvInt('MAX_ITEMS_PER_SCRAPE', 50),
  
  // Rate limiting
  REQUEST_DELAY_MS: getEnvInt('REQUEST_DELAY_MS', 1000),
  RATE_LIMIT_REQUESTS_PER_MINUTE: getEnvInt('RATE_LIMIT_REQUESTS_PER_MINUTE', 30),
  
  // Timeouts
  PAGE_TIMEOUT_MS: getEnvInt('PAGE_TIMEOUT_MS', 30000),
  NAVIGATION_TIMEOUT_MS: getEnvInt('NAVIGATION_TIMEOUT_MS', 60000),
  DOWNLOAD_TIMEOUT_MS: getEnvInt('DOWNLOAD_TIMEOUT_MS', 30000),
  
  // Memory management
  MAX_ASSETS_IN_MEMORY: getEnvInt('MAX_ASSETS_IN_MEMORY', 50),
  GARBAGE_COLLECTION_INTERVAL_MS: getEnvInt('GARBAGE_COLLECTION_INTERVAL_MS', 60000),
  
  // Scroll limits (for infinite scroll pages)
  MAX_SCROLLS: getEnvInt('MAX_SCROLLS', 5),
  SCROLL_DELAY_MS: getEnvInt('SCROLL_DELAY_MS', 1000),
};

/**
 * Browser configuration for low-RAM environments
 */
export const BROWSER_CONFIG = {
  headless: LIMITS.BROWSER_HEADLESS,
  args: [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--disable-extensions',
    '--disable-software-rasterizer',
    '--single-process', // Reduces memory usage
    '--no-zygote',
    `--js-flags=--max-old-space-size=${getEnvInt('MAX_HEAP_SIZE_MB', 512)}`,
  ],
};

/**
 * Context configuration for low-RAM environments
 */
export const CONTEXT_CONFIG = {
  viewport: { 
    width: 1280,  // Reduced from 1920
    height: 720   // Reduced from 1080
  },
  userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  locale: 'en-US',
  timezoneId: 'America/New_York',
  
  // Reduce resource usage
  javaScriptEnabled: true,
  bypassCSP: false,
  ignoreHTTPSErrors: true,
};

/**
 * Resource blocking configuration
 * Block unnecessary resources to reduce memory and bandwidth
 */
export const BLOCKED_RESOURCES = [
  'font',
  'stylesheet',
  'media', // Block video/audio unless needed
];

/**
 * Semaphore for limiting concurrent operations
 */
export class Semaphore {
  constructor(maxConcurrent) {
    this.maxConcurrent = maxConcurrent;
    this.current = 0;
    this.queue = [];
  }

  async acquire() {
    if (this.current < this.maxConcurrent) {
      this.current++;
      return;
    }

    return new Promise((resolve) => {
      this.queue.push(resolve);
    });
  }

  release() {
    this.current--;
    if (this.queue.length > 0) {
      this.current++;
      const next = this.queue.shift();
      next();
    }
  }
}

/**
 * Browser pool for managing browser instances
 */
export class BrowserPool {
  constructor(maxInstances = LIMITS.MAX_BROWSER_INSTANCES) {
    this.maxInstances = maxInstances;
    this.browsers = [];
    this.semaphore = new Semaphore(maxInstances);
  }

  async acquire(chromium) {
    await this.semaphore.acquire();
    
    const browser = await chromium.launch(BROWSER_CONFIG);
    this.browsers.push(browser);
    
    return browser;
  }

  async release(browser) {
    const index = this.browsers.indexOf(browser);
    if (index > -1) {
      this.browsers.splice(index, 1);
    }
    
    try {
      await browser.close();
    } catch (e) {
      // Browser may already be closed
    }
    
    this.semaphore.release();
  }

  async closeAll() {
    const closePromises = this.browsers.map(async (browser) => {
      try {
        await browser.close();
      } catch (e) {
        // Ignore errors
      }
    });
    
    await Promise.all(closePromises);
    this.browsers = [];
  }
}

/**
 * Job counter for enforcing global job cap
 */
export class JobCounter {
  constructor(maxJobs = LIMITS.GLOBAL_JOB_CAP) {
    this.maxJobs = maxJobs;
    this.currentJobs = 0;
    this.totalProcessed = 0;
  }

  canStartJob() {
    return this.currentJobs < this.maxJobs && this.totalProcessed < this.maxJobs;
  }

  startJob() {
    if (!this.canStartJob()) {
      throw new Error(`Job limit reached: ${this.totalProcessed}/${this.maxJobs}`);
    }
    this.currentJobs++;
    this.totalProcessed++;
  }

  endJob() {
    this.currentJobs--;
  }

  getStatus() {
    return {
      current: this.currentJobs,
      total: this.totalProcessed,
      max: this.maxJobs,
      remaining: this.maxJobs - this.totalProcessed,
    };
  }
}

/**
 * Memory monitor
 */
export function getMemoryUsage() {
  const usage = process.memoryUsage();
  return {
    heapUsed: Math.round(usage.heapUsed / 1024 / 1024),
    heapTotal: Math.round(usage.heapTotal / 1024 / 1024),
    rss: Math.round(usage.rss / 1024 / 1024),
    external: Math.round(usage.external / 1024 / 1024),
  };
}

/**
 * Force garbage collection if available
 */
export function forceGC() {
  if (global.gc) {
    global.gc();
    return true;
  }
  return false;
}

/**
 * Log limits configuration
 */
export function logLimitsConfig() {
  console.log('='.repeat(60));
  console.log('LOW-RAM SAFETY LIMITS');
  console.log('='.repeat(60));
  console.log(`Max Browser Instances: ${LIMITS.MAX_BROWSER_INSTANCES}`);
  console.log(`Headless Mode: ${LIMITS.BROWSER_HEADLESS}`);
  console.log(`Sequential Scraping: ${LIMITS.SEQUENTIAL_SCRAPING}`);
  console.log(`Max Concurrent Scrapes: ${LIMITS.MAX_CONCURRENT_SCRAPES}`);
  console.log(`Image Only Mode: ${LIMITS.IMAGE_ONLY_MODE}`);
  console.log(`Max Image Dimension: ${LIMITS.MAX_IMAGE_DIMENSION}px`);
  console.log(`Global Job Cap: ${LIMITS.GLOBAL_JOB_CAP}`);
  console.log(`Request Delay: ${LIMITS.REQUEST_DELAY_MS}ms`);
  console.log('='.repeat(60));
}

export default {
  LIMITS,
  BROWSER_CONFIG,
  CONTEXT_CONFIG,
  BLOCKED_RESOURCES,
  Semaphore,
  BrowserPool,
  JobCounter,
  getMemoryUsage,
  forceGC,
  logLimitsConfig,
};

