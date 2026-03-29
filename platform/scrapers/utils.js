/**
 * Utility functions for the Agentic Ads Scrapers
 *
 * Provides common functionality for rate limiting, retry logic,
 * image processing, and data validation.
 */

import { createLogger, format, transports } from 'winston';
import sharp from 'sharp';
import { v4 as uuidv4 } from 'uuid';
import crypto from 'crypto';

// ============================================================================
// Logger Configuration
// ============================================================================

const logger = createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: format.combine(format.timestamp(), format.errors({ stack: true }), format.json()),
  defaultMeta: { service: 'agentic-ads-scraper' },
  transports: [
    new transports.Console({
      format: format.combine(format.colorize(), format.simple())
    }),
    new transports.File({
      filename: 'logs/scraper-error.log',
      level: 'error'
    }),
    new transports.File({
      filename: 'logs/scraper.log'
    })
  ]
});

export { logger };

// ============================================================================
// Rate Limiting
// ============================================================================

/**
 * Rate limiter using token bucket algorithm
 */
export class RateLimiter {
  constructor(requestsPerMinute, burstSize = null) {
    this.requestsPerMinute = requestsPerMinute;
    this.burstSize = burstSize || Math.ceil(requestsPerMinute / 10);
    this.tokens = this.burstSize;
    this.lastRefill = Date.now();
    this.refillRate = 60000 / requestsPerMinute; // ms per token
  }

  async acquire() {
    this._refillTokens();

    if (this.tokens > 0) {
      this.tokens--;
      return true;
    }

    // Wait for a token to become available
    const waitTime = this.refillRate - (Date.now() - this.lastRefill);
    await this.sleep(Math.max(0, waitTime));
    return this.acquire();
  }

  _refillTokens() {
    const now = Date.now();
    const elapsed = now - this.lastRefill;
    const newTokens = Math.floor(elapsed / this.refillRate);

    if (newTokens > 0) {
      this.tokens = Math.min(this.burstSize, this.tokens + newTokens);
      this.lastRefill = now;
    }
  }

  sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

// ============================================================================
// Retry Logic
// ============================================================================

/**
 * Retry a function with exponential backoff
 */
export async function retryWithBackoff(fn, options = {}) {
  const {
    maxRetries = 3,
    initialDelay = 1000,
    maxDelay = 30000,
    factor = 2,
    onRetry = null,
    retryOn = (_error) => true
  } = options;

  let lastError;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      if (attempt === maxRetries || !retryOn(error)) {
        throw error;
      }

      const delay = Math.min(initialDelay * Math.pow(factor, attempt), maxDelay);

      if (onRetry) {
        onRetry(error, attempt + 1, delay);
      }

      logger.warn(`Retry attempt ${attempt + 1}/${maxRetries} after ${delay}ms`, {
        error: error.message
      });

      await sleep(delay);
    }
  }

  throw lastError;
}

export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ============================================================================
// Image Processing
// ============================================================================

/**
 * Process and optimize an image for storage
 */
export async function processImage(buffer, options = {}) {
  const { maxWidth = 1920, maxHeight = 1080, quality = 85, format = 'webp' } = options;

  try {
    let image = sharp(buffer);
    const metadata = await image.metadata();

    // Resize if larger than max dimensions
    if (metadata.width > maxWidth || metadata.height > maxHeight) {
      image = image.resize(maxWidth, maxHeight, {
        fit: 'inside',
        withoutEnlargement: true
      });
    }

    // Convert to specified format
    switch (format) {
      case 'webp':
        image = image.webp({ quality });
        break;
      case 'jpeg':
        image = image.jpeg({ quality });
        break;
      case 'png':
        image = image.png({ compressionLevel: 9 });
        break;
      default:
        image = image.webp({ quality });
    }

    const processedBuffer = await image.toBuffer();
    const processedMetadata = await sharp(processedBuffer).metadata();

    return {
      buffer: processedBuffer,
      metadata: {
        width: processedMetadata.width,
        height: processedMetadata.height,
        format: processedMetadata.format,
        size: processedBuffer.length,
        originalSize: buffer.length,
        compressionRatio: (buffer.length / processedBuffer.length).toFixed(2)
      }
    };
  } catch (error) {
    logger.error('Image processing failed', { error: error.message });
    throw error;
  }
}

/**
 * Extract key frames from a video URL
 */
export async function extractVideoKeyFrames(videoUrl, options = {}) {
  const { numFrames = 5 } = options;

  // Placeholder - in production, use ffmpeg or a video processing service
  logger.info('Video key frame extraction requested', { videoUrl, numFrames });

  return {
    frames: [],
    metadata: {
      videoUrl,
      numFrames,
      extracted: false,
      reason: 'Video processing not implemented in MVP'
    }
  };
}

// ============================================================================
// Data Validation
// ============================================================================

/**
 * Validate and sanitize scraped ad data
 */
export function validateAdData(data) {
  const errors = [];
  const warnings = [];

  // Required fields
  if (!data.sourceUrl) {
    errors.push('Missing required field: sourceUrl');
  }

  if (!data.source) {
    errors.push('Missing required field: source');
  }

  // Validate URL format
  if (data.sourceUrl && !isValidUrl(data.sourceUrl)) {
    errors.push('Invalid sourceUrl format');
  }

  if (data.imageUrl && !isValidUrl(data.imageUrl)) {
    warnings.push('Invalid imageUrl format');
  }

  // Validate date format
  if (data.publishedDate && !isValidDate(data.publishedDate)) {
    warnings.push('Invalid publishedDate format');
  }

  // Sanitize text fields
  const sanitizedData = {
    ...data,
    title: sanitizeText(data.title),
    description: sanitizeText(data.description),
    advertiserName: sanitizeText(data.advertiserName),
    ctaText: sanitizeText(data.ctaText)
  };

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    data: sanitizedData
  };
}

function isValidUrl(string) {
  try {
    new URL(string);
    return true;
  } catch {
    return false;
  }
}

function isValidDate(string) {
  const date = new Date(string);
  return !isNaN(date.getTime());
}

function sanitizeText(text) {
  if (!text) return null;
  return text.trim().replace(/\s+/g, ' ').substring(0, 10000); // Limit length
}

// ============================================================================
// ID Generation
// ============================================================================

/**
 * Generate a unique asset ID
 */
export function generateAssetId(source, sourceId) {
  return `${source}-${sourceId || uuidv4()}`;
}

/**
 * Generate a content hash for deduplication
 */
export function generateContentHash(content) {
  if (Buffer.isBuffer(content)) {
    return crypto.createHash('sha256').update(content).digest('hex');
  }
  return crypto.createHash('sha256').update(JSON.stringify(content)).digest('hex');
}

// ============================================================================
// Browser Utilities
// ============================================================================

/**
 * Wait for network idle with timeout
 */
export async function waitForNetworkIdle(page, options = {}) {
  const { timeout = 30000 } = options;

  try {
    await page.waitForLoadState('networkidle', { timeout });
  } catch (error) {
    logger.warn('Network idle timeout, continuing anyway');
  }
}

/**
 * Scroll to load lazy content
 */
export async function scrollToLoadContent(page, options = {}) {
  const { scrollDelay = 500, maxScrolls = 10, scrollAmount = 500 } = options;

  for (let i = 0; i < maxScrolls; i++) {
    await page.evaluate((amount) => {
      window.scrollBy(0, amount);
    }, scrollAmount);

    await sleep(scrollDelay);

    // Check if we've reached the bottom
    const isAtBottom = await page.evaluate(() => {
      return window.innerHeight + window.scrollY >= document.body.scrollHeight;
    });

    if (isAtBottom) break;
  }
}

/**
 * Extract all images from the current page
 */
export async function extractPageImages(page, options = {}) {
  const { minWidth = 100, minHeight = 100 } = options;

  return await page.evaluate(
    ({ minWidth, minHeight }) => {
      const images = Array.from(document.querySelectorAll('img'));

      return images
        .filter((img) => {
          return (
            img.naturalWidth >= minWidth &&
            img.naturalHeight >= minHeight &&
            img.src &&
            !img.src.startsWith('data:')
          );
        })
        .map((img) => ({
          src: img.src,
          alt: img.alt || null,
          width: img.naturalWidth,
          height: img.naturalHeight
        }));
    },
    { minWidth, minHeight }
  );
}

// ============================================================================
// Scraper Source Configuration
// ============================================================================

export const SCRAPER_SOURCES = {
  META_AD_LIBRARY: {
    id: 'meta_ad_library',
    name: 'Meta Ad Library',
    baseUrl: 'https://www.facebook.com/ads/library/',
    rateLimit: 30,
    selectors: {
      adCard: '[data-testid="ad_library_preview_card"]',
      adImage: 'img[src*="scontent"]',
      advertiserName: '[data-testid="ad_library_preview_advertiser_name"]',
      pageLink: 'a[href*="/ads/library/?active_status"]'
    }
  },
  GOOGLE_ADS_TRANSPARENCY: {
    id: 'google_ads_transparency',
    name: 'Google Ads Transparency Center',
    baseUrl: 'https://adstransparency.google.com/',
    rateLimit: 60,
    selectors: {
      adCard: '.creative-card',
      adImage: '.creative-image img',
      advertiserName: '.advertiser-name'
    }
  },
  INTERNET_ARCHIVE: {
    id: 'internet_archive',
    name: 'Internet Archive Ads',
    baseUrl: 'https://archive.org/details/tvnews',
    rateLimit: 120,
    selectors: {
      adCard: '.item-ia',
      adImage: '.item-img img',
      title: '.item-ttl'
    }
  },
  WIKIMEDIA_COMMONS: {
    id: 'wikimedia_commons',
    name: 'Wikimedia Commons',
    baseUrl: 'https://commons.wikimedia.org/',
    rateLimit: 100,
    selectors: {
      fileCard: '.gallerybox',
      fileImage: '.gallerybox img',
      fileTitle: '.gallerytext'
    }
  }
};

// ============================================================================
// Output Formatting
// ============================================================================

/**
 * Format scraped data for output
 */
export function formatOutput(assets, metadata = {}) {
  return {
    success: true,
    timestamp: new Date().toISOString(),
    source: metadata.source || 'unknown',
    count: assets.length,
    assets: assets.map((asset) => ({
      id: asset.id || generateAssetId(metadata.source, asset.sourceId),
      ...asset,
      scrapedAt: new Date().toISOString()
    })),
    metadata: {
      ...metadata,
      processingTime: metadata.processingTime || null,
      errors: metadata.errors || []
    }
  };
}

/**
 * Format error output
 */
export function formatError(error, metadata = {}) {
  return {
    success: false,
    timestamp: new Date().toISOString(),
    source: metadata.source || 'unknown',
    error: {
      message: error.message,
      code: error.code || 'UNKNOWN_ERROR',
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
    },
    metadata
  };
}
