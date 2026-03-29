#!/usr/bin/env node

/**
 * Agentic Ads Scraper - HTTP & WebSocket Server
 *
 * Provides an HTTP API for triggering scraping jobs and
 * WebSocket streaming for live browser viewing.
 * Designed for Cloud Run deployment with streaming support.
 */

import http from 'http';
import fs from 'fs';
import path from 'path';
import { URL } from 'url';
import { createScraper } from './scraper.js';
import { getStreamManager } from './streaming.js';
import { logger, formatOutput, formatError } from './utils.js';

const PORT = process.env.PORT || 3001;
const HOST = '0.0.0.0';
const SCREENSHOTS_DIR = process.env.SCREENSHOTS_DIR || './data/screenshots';

// Initialize stream manager
const streamManager = getStreamManager({
  screenshotsDir: SCREENSHOTS_DIR,
  screenshotInterval: parseInt(process.env.SCREENSHOT_INTERVAL || '2000', 10),
  frameQuality: parseInt(process.env.FRAME_QUALITY || '60', 10)
});

/**
 * Parse JSON body from request
 */
async function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => (body += chunk));
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (error) {
        reject(new Error('Invalid JSON body'));
      }
    });
    req.on('error', reject);
  });
}

/**
 * Send JSON response
 */
function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

/**
 * Handle scraping request with streaming support
 */
async function handleScrape(req, res) {
  const startTime = Date.now();
  let scraper = null;

  try {
    const body = await parseBody(req);

    const {
      source = 'meta_ad_library',
      query = null,
      filters = {},
      maxItems = 100,
      streaming = true,
      sessionId = null,
      jobId = null,
      headless = true
    } = body;

    logger.info('Starting scrape job', {
      source,
      query,
      maxItems,
      streaming,
      sessionId,
      headless
    });

    // Create scraper with streaming options
    scraper = createScraper(source, {
      streaming,
      sessionId,
      jobId,
      headless,
      streamManager
    });

    await scraper.initialize();

    const assets = await scraper.scrape(query, { ...filters, maxItems });

    const processingTime = Date.now() - startTime;
    const output = formatOutput(assets, {
      source,
      query,
      processingTime,
      errors: scraper.errors,
      sessionId: scraper.sessionId,
      screenshotCount: scraper.screenshotCount || 0
    });

    logger.info('Scrape job completed', {
      source,
      count: assets.length,
      processingTime,
      sessionId: scraper.sessionId
    });

    sendJson(res, 200, output);
  } catch (error) {
    logger.error('Scrape job failed', { error: error.message });
    const output = formatError(error, { source: 'unknown' });
    sendJson(res, 500, output);
  } finally {
    if (scraper) {
      await scraper.close();
    }
  }
}

/**
 * Health check handler
 */
function handleHealth(req, res) {
  sendJson(res, 200, {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    activeSessions: streamManager.getActiveSessions().length
  });
}

/**
 * Get active streaming sessions
 */
function handleActiveSessions(req, res) {
  const sessions = streamManager.getActiveSessions();
  sendJson(res, 200, { sessions });
}

/**
 * Get screenshots for a job/session
 */
function handleGetScreenshots(req, res, sessionId) {
  const sessionDir = path.join(SCREENSHOTS_DIR, sessionId);

  if (!fs.existsSync(sessionDir)) {
    sendJson(res, 200, {
      session_id: sessionId,
      count: 0,
      screenshots: []
    });
    return;
  }

  const screenshots = [];
  const files = fs
    .readdirSync(sessionDir)
    .filter((f) => f.endsWith('.jpg'))
    .sort();

  for (const filename of files) {
    const metaPath = path.join(sessionDir, `${filename}.json`);
    let meta = {};

    if (fs.existsSync(metaPath)) {
      try {
        meta = JSON.parse(fs.readFileSync(metaPath, 'utf-8'));
      } catch (e) {
        // Ignore parse errors
      }
    }

    screenshots.push({
      filename,
      url: `/screenshots/${sessionId}/${filename}`,
      timestamp: meta.timestamp,
      page_url: meta.url,
      action: meta.action,
      step: meta.step
    });
  }

  sendJson(res, 200, {
    session_id: sessionId,
    count: screenshots.length,
    screenshots
  });
}

/**
 * Serve screenshot image
 */
function handleServeScreenshot(req, res, sessionId, filename) {
  const filePath = path.join(SCREENSHOTS_DIR, sessionId, filename);

  if (!fs.existsSync(filePath)) {
    sendJson(res, 404, { error: 'Screenshot not found' });
    return;
  }

  const stat = fs.statSync(filePath);
  res.writeHead(200, {
    'Content-Type': 'image/jpeg',
    'Content-Length': stat.size,
    'Cache-Control': 'public, max-age=3600'
  });
  fs.createReadStream(filePath).pipe(res);
}

/**
 * Get list of sessions with screenshots
 */
function handleSessionsWithScreenshots(req, res) {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    sendJson(res, 200, { sessions: [], count: 0 });
    return;
  }

  const sessions = fs.readdirSync(SCREENSHOTS_DIR).filter((dir) => {
    const dirPath = path.join(SCREENSHOTS_DIR, dir);
    return (
      fs.statSync(dirPath).isDirectory() && fs.readdirSync(dirPath).some((f) => f.endsWith('.jpg'))
    );
  });

  sendJson(res, 200, {
    sessions: sessions.sort(),
    count: sessions.length
  });
}

/**
 * Main request handler
 */
async function handleRequest(req, res) {
  const url = new URL(req.url, `http://${HOST}:${PORT}`);
  const path = url.pathname;
  const method = req.method;

  logger.debug(`${method} ${path}`);

  // CORS headers for development
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  try {
    // Route matching
    if (path === '/health' && method === 'GET') {
      handleHealth(req, res);
      return;
    }

    if (path === '/scrape' && method === 'POST') {
      await handleScrape(req, res);
      return;
    }

    if (path === '/sources' && method === 'GET') {
      sendJson(res, 200, {
        sources: [
          'meta_ad_library',
          'google_ads_transparency',
          'internet_archive',
          'wikimedia_commons'
        ]
      });
      return;
    }

    if (path === '/sessions/active' && method === 'GET') {
      handleActiveSessions(req, res);
      return;
    }

    if (path === '/sessions/with-screenshots' && method === 'GET') {
      handleSessionsWithScreenshots(req, res);
      return;
    }

    // Pattern: /sessions/:sessionId/screenshots
    const screenshotsMatch = path.match(/^\/sessions\/([^/]+)\/screenshots$/);
    if (screenshotsMatch && method === 'GET') {
      handleGetScreenshots(req, res, screenshotsMatch[1]);
      return;
    }

    // Pattern: /screenshots/:sessionId/:filename
    const screenshotFileMatch = path.match(/^\/screenshots\/([^/]+)\/([^/]+)$/);
    if (screenshotFileMatch && method === 'GET') {
      handleServeScreenshot(req, res, screenshotFileMatch[1], screenshotFileMatch[2]);
      return;
    }

    sendJson(res, 404, { error: 'Not found' });
  } catch (error) {
    logger.error('Request handler error', { error: error.message });
    sendJson(res, 500, { error: 'Internal server error' });
  }
}

/**
 * Start the server
 */
const server = http.createServer(handleRequest);

// Initialize WebSocket server on the same HTTP server
streamManager.initWebSocketServer(server);

server.listen(PORT, HOST, () => {
  logger.info(`Scraper server listening on ${HOST}:${PORT}`);
  logger.info(`WebSocket streaming available at ws://${HOST}:${PORT}/ws/stream`);
  logger.info(`Screenshots directory: ${SCREENSHOTS_DIR}`);
});

// Graceful shutdown
async function shutdown(signal) {
  logger.info(`${signal} received, shutting down...`);

  await streamManager.shutdown();

  server.close(() => {
    logger.info('Server closed');
    process.exit(0);
  });

  // Force exit after 10 seconds
  setTimeout(() => {
    logger.warn('Forced shutdown after timeout');
    process.exit(1);
  }, 10000);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

export default server;
