#!/usr/bin/env node

/**
 * Public Ads Scraper - Main Entry Point
 *
 * A Playwright-based scraper for collecting public ads from multiple
 * public sources: Meta Ad Library, Google Ads Transparency Center,
 * Internet Archive, and Wikimedia Commons.
 *
 * Usage:
 *   node scraper.js --source meta_ad_library --query "finance"
 *   node scraper.js --source google_ads_transparency --filters '{"region":"US"}'
 */

import { chromium } from 'playwright';
import { program } from 'commander';
import dotenv from 'dotenv';
import { v4 as uuidv4 } from 'uuid';
import {
  logger,
  RateLimiter,
  retryWithBackoff,
  processImage,
  validateAdData,
  generateAssetId,
  generateContentHash,
  waitForNetworkIdle,
  scrollToLoadContent,
  extractPageImages,
  formatOutput,
  formatError,
  SCRAPER_SOURCES,
  sleep
} from './utils.js';

// Load environment variables
dotenv.config();

// ============================================================================
// Scraper Base Class
// ============================================================================

class BaseScraper {
  constructor(config, options = {}) {
    this.config = config;
    this.browser = null;
    this.context = null;
    this.mainPage = null; // Main page for streaming
    this.rateLimiter = new RateLimiter(config.rateLimit || 60);
    this.results = [];
    this.errors = [];

    // Streaming options
    this.streamingEnabled = options.streaming ?? false;
    this.headless = options.headless ?? process.env.HEADLESS !== 'false';
    this.sessionId = options.sessionId || uuidv4();
    this.jobId = options.jobId || null;
    this.streamManager = options.streamManager || null;
    this.screenshotCount = 0;

    logger.info('BaseScraper created', {
      source: config.name,
      sessionId: this.sessionId,
      streaming: this.streamingEnabled,
      headless: this.headless
    });
  }

  async initialize() {
    logger.info(`Initializing ${this.config.name} scraper`, {
      sessionId: this.sessionId,
      streaming: this.streamingEnabled,
      headless: this.headless
    });

    this.browser = await chromium.launch({
      headless: this.headless,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
    });

    this.context = await this.browser.newContext({
      viewport: { width: 1280, height: 720 },
      userAgent:
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      locale: 'en-US',
      timezoneId: 'America/New_York'
    });

    // Don't block stylesheets when streaming (better visuals)
    if (!this.streamingEnabled) {
      await this.context.route('**/*', (route) => {
        const resourceType = route.request().resourceType();
        if (['font', 'stylesheet'].includes(resourceType)) {
          route.abort();
        } else {
          route.continue();
        }
      });
    }

    // Create main page for streaming
    this.mainPage = await this.context.newPage();

    // Start screencast if streaming is enabled
    if (this.streamingEnabled && this.streamManager) {
      await this.streamManager.startScreencast(this.sessionId, this.mainPage, {
        jobId: this.jobId,
        source: this.config.name
      });
      logger.info('Screencast started', { sessionId: this.sessionId });
    }
  }

  async close() {
    // Stop screencast if streaming
    if (this.streamingEnabled && this.streamManager) {
      await this.streamManager.stopScreencast(this.sessionId);
      this.screenshotCount =
        this.streamManager.getSessionInfo(this.sessionId)?.screenshot_count || 0;
      logger.info('Screencast stopped', {
        sessionId: this.sessionId,
        screenshotCount: this.screenshotCount
      });
    }

    if (this.mainPage) {
      await this.mainPage.close();
    }
    if (this.context) {
      await this.context.close();
    }
    if (this.browser) {
      await this.browser.close();
    }
    logger.info(`Closed ${this.config.name} scraper`, { sessionId: this.sessionId });
  }

  /**
   * Get the page to use for scraping.
   * Returns mainPage for streaming mode, or creates a new page otherwise.
   */
  async getScrapingPage() {
    if (this.streamingEnabled && this.mainPage) {
      return this.mainPage;
    }
    return await this.context.newPage();
  }

  /**
   * Close a scraping page if it's not the main streaming page.
   */
  async closeScrapingPage(page) {
    if (page !== this.mainPage) {
      await page.close();
    }
  }

  async scrape(query, _filters = {}) {
    throw new Error('scrape() must be implemented by subclass');
  }

  async downloadImage(url) {
    try {
      await this.rateLimiter.acquire();

      const page = await this.context.newPage();
      const response = await page.goto(url, { waitUntil: 'load', timeout: 30000 });
      const buffer = await response.body();
      await page.close();

      return await processImage(buffer);
    } catch (error) {
      logger.error('Failed to download image', { url, error: error.message });
      return null;
    }
  }
}

// ============================================================================
// Meta Ad Library Scraper
// ============================================================================

class MetaAdLibraryScraper extends BaseScraper {
  constructor(options = {}) {
    super(SCRAPER_SOURCES.META_AD_LIBRARY, options);
  }

  async scrape(query, filters = {}) {
    const page = await this.getScrapingPage();
    const ads = [];

    try {
      const searchUrl = this.buildSearchUrl(query, filters);
      logger.info('Scraping Meta Ad Library', { url: searchUrl, sessionId: this.sessionId });

      await this.rateLimiter.acquire();
      await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await waitForNetworkIdle(page, { timeout: 10000 });

      // Handle cookie consent if present
      try {
        await page.click('[data-testid="cookie-policy-manage-dialog-accept-button"]', {
          timeout: 3000
        });
      } catch {
        // Cookie dialog not present
      }

      // Wait for ads to load
      await page.waitForSelector(this.config.selectors.adCard, { timeout: 15000 }).catch(() => {
        logger.warn('No ad cards found');
      });

      // Scroll to load more ads
      await scrollToLoadContent(page, { maxScrolls: 5 });

      // Extract ad data
      const adElements = await page.$$(this.config.selectors.adCard);
      logger.info(`Found ${adElements.length} ad elements`, { sessionId: this.sessionId });

      for (const element of adElements.slice(0, filters.maxItems || 100)) {
        try {
          const adData = await this.extractAdData(element, page);
          if (adData) {
            const validation = validateAdData(adData);
            if (validation.isValid) {
              ads.push(validation.data);
            } else {
              this.errors.push({ type: 'validation', errors: validation.errors });
            }
          }
        } catch (error) {
          logger.error('Failed to extract ad data', { error: error.message });
          this.errors.push({ type: 'extraction', error: error.message });
        }
      }
    } catch (error) {
      logger.error('Meta Ad Library scraping failed', { error: error.message });
      throw error;
    } finally {
      await this.closeScrapingPage(page);
    }

    return ads;
  }

  buildSearchUrl(query, filters) {
    const params = new URLSearchParams({
      active_status: 'active',
      ad_type: 'all',
      country: filters.country || 'US',
      media_type: 'all',
      search_type: 'keyword_unordered'
    });

    if (query) {
      params.set('q', query);
    }

    return `${this.config.baseUrl}?${params.toString()}`;
  }

  async extractAdData(element, _page) {
    try {
      // Extract image URL
      const imageElement = await element.$(this.config.selectors.adImage);
      const imageUrl = imageElement ? await imageElement.getAttribute('src') : null;

      // Extract advertiser name
      const advertiserElement = await element.$(this.config.selectors.advertiserName);
      const advertiserName = advertiserElement ? await advertiserElement.textContent() : null;

      // Extract ad text
      const textElements = await element.$$('div[dir="auto"]');
      const texts = await Promise.all(textElements.map((el) => el.textContent()));
      const adText = texts.filter((t) => t && t.length > 10).join(' ');

      // Extract page link for source URL
      const linkElement = await element.$(this.config.selectors.pageLink);
      const sourceUrl = linkElement ? await linkElement.getAttribute('href') : null;

      if (!imageUrl && !adText) {
        return null;
      }

      return {
        id: generateAssetId('meta', generateContentHash({ imageUrl, adText })),
        source: 'meta_ad_library',
        sourceUrl: sourceUrl ? `https://www.facebook.com${sourceUrl}` : null,
        imageUrl,
        type: 'image',
        advertiserName,
        title: adText.substring(0, 100),
        description: adText,
        metadata: {
          platform: 'facebook',
          adType: 'display',
          country: 'US'
        }
      };
    } catch (error) {
      logger.error('Ad data extraction failed', { error: error.message });
      return null;
    }
  }
}

// ============================================================================
// Google Ads Transparency Center Scraper
// ============================================================================

class GoogleAdsTransparencyScraper extends BaseScraper {
  constructor(options = {}) {
    super(SCRAPER_SOURCES.GOOGLE_ADS_TRANSPARENCY, options);
  }

  async scrape(query, filters = {}) {
    const page = await this.getScrapingPage();
    const ads = [];

    try {
      const searchUrl = this.buildSearchUrl(query, filters);
      logger.info('Scraping Google Ads Transparency Center', {
        url: searchUrl,
        sessionId: this.sessionId
      });

      await this.rateLimiter.acquire();
      await page.goto(searchUrl, { waitUntil: 'networkidle', timeout: 60000 });

      // Wait for content to load
      await sleep(3000);

      // Search for ads if query provided
      if (query) {
        const searchInput = await page.$('input[type="text"]');
        if (searchInput) {
          await searchInput.fill(query);
          await searchInput.press('Enter');
          await sleep(3000);
        }
      }

      // Scroll to load more content
      await scrollToLoadContent(page, { maxScrolls: 5 });

      // Extract ad creatives
      const images = await extractPageImages(page, { minWidth: 150, minHeight: 150 });

      for (const image of images.slice(0, filters.maxItems || 100)) {
        const adData = {
          id: generateAssetId('google', generateContentHash(image.src)),
          source: 'google_ads_transparency',
          sourceUrl: page.url(),
          imageUrl: image.src,
          type: 'image',
          title: image.alt || 'Google Ad Creative',
          metadata: {
            platform: 'google',
            width: image.width,
            height: image.height
          }
        };

        const validation = validateAdData(adData);
        if (validation.isValid) {
          ads.push(validation.data);
        }
      }
    } catch (error) {
      logger.error('Google Ads Transparency scraping failed', { error: error.message });
      throw error;
    } finally {
      await this.closeScrapingPage(page);
    }

    return ads;
  }

  buildSearchUrl(_query, filters) {
    const params = new URLSearchParams();
    if (filters.region) params.set('region', filters.region);

    const queryString = params.toString();
    return `${this.config.baseUrl}${queryString ? '?' + queryString : ''}`;
  }
}

// ============================================================================
// Internet Archive Scraper
// ============================================================================

class InternetArchiveScraper extends BaseScraper {
  constructor(options = {}) {
    super(SCRAPER_SOURCES.INTERNET_ARCHIVE, options);
  }

  async scrape(query, filters = {}) {
    const page = await this.getScrapingPage();
    const ads = [];

    try {
      const searchUrl = this.buildSearchUrl(query, filters);
      logger.info('Scraping Internet Archive', { url: searchUrl, sessionId: this.sessionId });

      await this.rateLimiter.acquire();
      await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await waitForNetworkIdle(page, { timeout: 15000 });

      // Scroll to load more content
      await scrollToLoadContent(page, { maxScrolls: 3 });

      // Extract items
      const items = await page.$$(this.config.selectors.adCard);
      logger.info(`Found ${items.length} archive items`, { sessionId: this.sessionId });

      for (const item of items.slice(0, filters.maxItems || 100)) {
        try {
          const imageEl = await item.$(this.config.selectors.adImage);
          const titleEl = await item.$(this.config.selectors.title);
          const linkEl = await item.$('a');

          const imageUrl = imageEl ? await imageEl.getAttribute('src') : null;
          const title = titleEl ? await titleEl.textContent() : null;
          const href = linkEl ? await linkEl.getAttribute('href') : null;

          if (imageUrl || title) {
            const adData = {
              id: generateAssetId('archive', href || generateContentHash({ imageUrl, title })),
              source: 'internet_archive',
              sourceUrl: href ? `https://archive.org${href}` : null,
              imageUrl: imageUrl ? `https://archive.org${imageUrl}` : null,
              type: 'image',
              title: title?.trim(),
              metadata: {
                platform: 'internet_archive',
                category: 'tvnews'
              }
            };

            const validation = validateAdData(adData);
            if (validation.isValid) {
              ads.push(validation.data);
            }
          }
        } catch (error) {
          this.errors.push({ type: 'extraction', error: error.message });
        }
      }
    } catch (error) {
      logger.error('Internet Archive scraping failed', { error: error.message });
      throw error;
    } finally {
      await this.closeScrapingPage(page);
    }

    return ads;
  }

  buildSearchUrl(query, _filters) {
    const params = new URLSearchParams({
      query: query || 'advertisement',
      sort: '-date'
    });

    return `https://archive.org/search?${params.toString()}`;
  }
}

// ============================================================================
// Wikimedia Commons Scraper
// ============================================================================

class WikimediaCommonsScraper extends BaseScraper {
  constructor(options = {}) {
    super(SCRAPER_SOURCES.WIKIMEDIA_COMMONS, options);
  }

  async scrape(query, filters = {}) {
    const page = await this.getScrapingPage();
    const ads = [];

    try {
      const searchUrl = this.buildSearchUrl(query, filters);
      logger.info('Scraping Wikimedia Commons', { url: searchUrl, sessionId: this.sessionId });

      await this.rateLimiter.acquire();
      await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await waitForNetworkIdle(page, { timeout: 10000 });

      // Extract gallery items
      const items = await page.$$(this.config.selectors.fileCard);
      logger.info(`Found ${items.length} Wikimedia items`, { sessionId: this.sessionId });

      for (const item of items.slice(0, filters.maxItems || 100)) {
        try {
          const imageEl = await item.$(this.config.selectors.fileImage);
          const titleEl = await item.$(this.config.selectors.fileTitle);
          const linkEl = await item.$('a.image');

          const imageUrl = imageEl ? await imageEl.getAttribute('src') : null;
          const title = titleEl ? await titleEl.textContent() : null;
          const href = linkEl ? await linkEl.getAttribute('href') : null;

          if (imageUrl) {
            const adData = {
              id: generateAssetId('wikimedia', href || generateContentHash(imageUrl)),
              source: 'wikimedia_commons',
              sourceUrl: href ? `https://commons.wikimedia.org${href}` : null,
              imageUrl: imageUrl.startsWith('//') ? `https:${imageUrl}` : imageUrl,
              type: 'image',
              title: title?.trim(),
              metadata: {
                platform: 'wikimedia',
                license: 'Creative Commons'
              }
            };

            const validation = validateAdData(adData);
            if (validation.isValid) {
              ads.push(validation.data);
            }
          }
        } catch (error) {
          this.errors.push({ type: 'extraction', error: error.message });
        }
      }
    } catch (error) {
      logger.error('Wikimedia Commons scraping failed', { error: error.message });
      throw error;
    } finally {
      await this.closeScrapingPage(page);
    }

    return ads;
  }

  buildSearchUrl(_query, _filters) {
    return `${this.config.baseUrl}wiki/Category:Advertisements`;
  }
}

// ============================================================================
// Scraper Factory
// ============================================================================

/**
 * Create a scraper instance for the given source.
 * @param {string} source - Scraper source name
 * @param {object} options - Scraper options
 * @param {boolean} options.streaming - Enable CDP screencast streaming
 * @param {boolean} options.headless - Run in headless mode
 * @param {string} options.sessionId - Unique session ID for streaming
 * @param {string} options.jobId - Job ID for tracking
 * @param {StreamManager} options.streamManager - StreamManager instance
 */
function createScraper(source, options = {}) {
  switch (source) {
    case 'meta_ad_library':
      return new MetaAdLibraryScraper(options);
    case 'google_ads_transparency':
      return new GoogleAdsTransparencyScraper(options);
    case 'internet_archive':
      return new InternetArchiveScraper(options);
    case 'wikimedia_commons':
      return new WikimediaCommonsScraper(options);
    default:
      throw new Error(`Unknown scraper source: ${source}`);
  }
}

// ============================================================================
// CLI Interface
// ============================================================================

program
  .name('public-ads-scraper')
  .description('Scrape public ads from public sources')
  .version('1.0.0');

program
  .option(
    '-s, --source <source>',
    'Scraper source (meta_ad_library, google_ads_transparency, internet_archive, wikimedia_commons)'
  )
  .option('-q, --query <query>', 'Search query')
  .option('-f, --filters <json>', 'JSON filters object')
  .option('-o, --output <file>', 'Output file path')
  .option('--max-items <number>', 'Maximum items to scrape', '100')
  .option('--headless <boolean>', 'Run in headless mode', 'true')
  .action(async (options) => {
    const startTime = Date.now();
    let scraper = null;

    try {
      const source = options.source || 'meta_ad_library';
      const query = options.query;
      const filters = options.filters ? JSON.parse(options.filters) : {};
      filters.maxItems = parseInt(options.maxItems, 10);

      logger.info('Starting scraper', { source, query, filters });

      scraper = createScraper(source);
      await scraper.initialize();

      const assets = await retryWithBackoff(() => scraper.scrape(query, filters), {
        maxRetries: 3
      });

      const processingTime = Date.now() - startTime;
      const output = formatOutput(assets, {
        source,
        query,
        processingTime,
        errors: scraper.errors
      });

      // Output results
      const outputJson = JSON.stringify(output, null, 2);

      if (options.output) {
        const fs = await import('fs/promises');
        await fs.writeFile(options.output, outputJson);
        logger.info(`Results written to ${options.output}`);
      } else {
        console.log(outputJson);
      }

      logger.info('Scraping completed', {
        source,
        count: assets.length,
        processingTime,
        errors: scraper.errors.length
      });
    } catch (error) {
      const output = formatError(error, { source: options.source });
      console.error(JSON.stringify(output));
      process.exit(1);
    } finally {
      if (scraper) {
        await scraper.close();
      }
    }
  });

program.parse();

export {
  BaseScraper,
  MetaAdLibraryScraper,
  GoogleAdsTransparencyScraper,
  InternetArchiveScraper,
  WikimediaCommonsScraper,
  createScraper
};
