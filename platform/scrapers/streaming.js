/**
 * Streaming Module - CDP Screencast and WebSocket Broadcasting
 * 
 * Provides real-time video streaming of Playwright browser sessions
 * using Chrome DevTools Protocol (CDP) screencast.
 */

import { WebSocketServer } from 'ws';
import fs from 'fs';
import path from 'path';
import { logger } from './utils.js';

// ============================================================================
// StreamManager - Manages CDP screencast sessions and WebSocket clients
// ============================================================================

export class StreamManager {
  constructor(options = {}) {
    this.sessions = new Map(); // sessionId -> session data
    this.wsClients = new Map(); // sessionId -> Set<WebSocket>
    this.wss = null;
    
    // Configuration
    this.screenshotInterval = options.screenshotInterval || 2000; // ms
    this.screenshotsDir = options.screenshotsDir || './data/screenshots';
    this.frameQuality = options.frameQuality || 60;
    this.maxWidth = options.maxWidth || 1280;
    this.maxHeight = options.maxHeight || 720;
    
    // Ensure screenshots directory exists
    if (!fs.existsSync(this.screenshotsDir)) {
      fs.mkdirSync(this.screenshotsDir, { recursive: true });
    }
    
    logger.info('StreamManager initialized', {
      screenshotInterval: this.screenshotInterval,
      screenshotsDir: this.screenshotsDir
    });
  }

  /**
   * Initialize WebSocket server
   * @param {http.Server} httpServer - HTTP server to attach to
   */
  initWebSocketServer(httpServer) {
    this.wss = new WebSocketServer({ 
      server: httpServer,
      path: '/ws/stream'
    });

    this.wss.on('connection', (ws, req) => {
      // Extract session ID from URL: /ws/stream?sessionId=xxx
      const url = new URL(req.url, `http://${req.headers.host}`);
      const sessionId = url.searchParams.get('sessionId');
      
      if (!sessionId) {
        ws.close(1008, 'Missing sessionId parameter');
        return;
      }

      logger.info('WebSocket client connected', { sessionId });
      
      // Register client for this session
      if (!this.wsClients.has(sessionId)) {
        this.wsClients.set(sessionId, new Set());
      }
      this.wsClients.get(sessionId).add(ws);

      // Send current session info if available
      const session = this.sessions.get(sessionId);
      if (session) {
        ws.send(JSON.stringify({
          type: 'session_info',
          session: this.getSessionInfo(sessionId)
        }));
      } else {
        ws.send(JSON.stringify({
          type: 'waiting',
          message: 'Waiting for scraper session to start...'
        }));
      }

      // Handle client messages (ping/pong)
      ws.on('message', (data) => {
        const msg = data.toString();
        if (msg === 'ping') {
          ws.send('pong');
        }
      });

      ws.on('close', () => {
        logger.info('WebSocket client disconnected', { sessionId });
        const clients = this.wsClients.get(sessionId);
        if (clients) {
          clients.delete(ws);
          if (clients.size === 0) {
            this.wsClients.delete(sessionId);
          }
        }
      });

      ws.on('error', (error) => {
        logger.error('WebSocket error', { sessionId, error: error.message });
      });
    });

    logger.info('WebSocket server initialized on /ws/stream');
  }

  /**
   * Start CDP screencast for a Playwright page
   * @param {string} sessionId - Unique session identifier
   * @param {Page} page - Playwright page object
   * @param {object} options - Screencast options
   */
  async startScreencast(sessionId, page, options = {}) {
    if (this.sessions.has(sessionId)) {
      logger.warn('Screencast already active for session', { sessionId });
      return;
    }

    const {
      jobId = null,
      source = 'unknown',
    } = options;

    try {
      // Create CDP session
      const cdpSession = await page.context().newCDPSession(page);
      
      // Session state
      const session = {
        sessionId,
        jobId,
        source,
        page,
        cdpSession,
        startedAt: Date.now(),
        frameCount: 0,
        screenshotCount: 0,
        lastScreenshotTime: 0,
        currentUrl: page.url(),
        isActive: true
      };
      
      this.sessions.set(sessionId, session);

      // Create session screenshots directory
      const sessionDir = path.join(this.screenshotsDir, sessionId);
      if (!fs.existsSync(sessionDir)) {
        fs.mkdirSync(sessionDir, { recursive: true });
      }

      // Handle screencast frames
      cdpSession.on('Page.screencastFrame', async (frame) => {
        await this.handleScreencastFrame(sessionId, frame);
      });

      // Start screencast
      await cdpSession.send('Page.startScreencast', {
        format: 'jpeg',
        quality: this.frameQuality,
        maxWidth: this.maxWidth,
        maxHeight: this.maxHeight,
        everyNthFrame: 1
      });

      logger.info('Started screencast', { sessionId, jobId, source });

      // Notify waiting clients
      this.broadcast(sessionId, {
        type: 'session_info',
        session: this.getSessionInfo(sessionId)
      });

    } catch (error) {
      logger.error('Failed to start screencast', { 
        sessionId, 
        error: error.message 
      });
      throw error;
    }
  }

  /**
   * Handle incoming screencast frame
   * @param {string} sessionId - Session identifier
   * @param {object} frame - CDP screencast frame
   */
  async handleScreencastFrame(sessionId, frame) {
    const session = this.sessions.get(sessionId);
    if (!session || !session.isActive) return;

    session.frameCount++;
    session.currentUrl = session.page.url();

    // Acknowledge frame to continue receiving
    try {
      await session.cdpSession.send('Page.screencastFrameAck', {
        sessionId: frame.sessionId
      });
    } catch (error) {
      // Session may have ended
      return;
    }

    // Broadcast frame to WebSocket clients
    this.broadcast(sessionId, {
      type: 'frame',
      data: frame.data,
      timestamp: new Date().toISOString(),
      metadata: frame.metadata,
      url: session.currentUrl
    });

    // Save periodic screenshots for replay
    const now = Date.now();
    if (now - session.lastScreenshotTime >= this.screenshotInterval) {
      await this.saveScreenshot(sessionId, frame.data, {
        url: session.currentUrl,
        action: 'auto_screenshot',
        step: 'scraping'
      });
      session.lastScreenshotTime = now;
      session.screenshotCount++;
    }
  }

  /**
   * Save screenshot to disk
   * @param {string} sessionId - Session identifier
   * @param {string} frameData - Base64 encoded JPEG data
   * @param {object} metadata - Screenshot metadata
   */
  async saveScreenshot(sessionId, frameData, metadata = {}) {
    const session = this.sessions.get(sessionId);
    if (!session) return;

    const timestamp = new Date();
    const filename = `${timestamp.toISOString().replace(/[:.]/g, '-')}.jpg`;
    const sessionDir = path.join(this.screenshotsDir, sessionId);
    const imagePath = path.join(sessionDir, filename);
    const metaPath = path.join(sessionDir, `${filename}.json`);

    try {
      // Save image
      const imageBuffer = Buffer.from(frameData, 'base64');
      fs.writeFileSync(imagePath, imageBuffer);

      // Save metadata
      const metaContent = {
        timestamp: timestamp.toISOString(),
        url: metadata.url,
        action: metadata.action,
        step: metadata.step,
        jobId: session.jobId,
        source: session.source
      };
      fs.writeFileSync(metaPath, JSON.stringify(metaContent, null, 2));

      logger.debug('Screenshot saved', { sessionId, filename });
    } catch (error) {
      logger.error('Failed to save screenshot', { 
        sessionId, 
        error: error.message 
      });
    }
  }

  /**
   * Update session context (e.g., current action)
   * @param {string} sessionId - Session identifier
   * @param {object} context - Context update
   */
  updateContext(sessionId, context) {
    const session = this.sessions.get(sessionId);
    if (session) {
      Object.assign(session, context);
      
      // Broadcast context update
      this.broadcast(sessionId, {
        type: 'context_update',
        context: {
          url: session.currentUrl,
          ...context
        }
      });
    }
  }

  /**
   * Stop screencast for a session
   * @param {string} sessionId - Session identifier
   */
  async stopScreencast(sessionId) {
    const session = this.sessions.get(sessionId);
    if (!session) return;

    session.isActive = false;

    try {
      await session.cdpSession.send('Page.stopScreencast');
      await session.cdpSession.detach();
    } catch (error) {
      // Session may already be closed
    }

    // Notify clients
    this.broadcast(sessionId, {
      type: 'stream_ended',
      session: this.getSessionInfo(sessionId)
    });

    logger.info('Stopped screencast', { 
      sessionId,
      frameCount: session.frameCount,
      screenshotCount: session.screenshotCount,
      duration: Date.now() - session.startedAt
    });

    this.sessions.delete(sessionId);
  }

  /**
   * Broadcast message to all clients of a session
   * @param {string} sessionId - Session identifier
   * @param {object} message - Message to broadcast
   */
  broadcast(sessionId, message) {
    const clients = this.wsClients.get(sessionId);
    if (!clients || clients.size === 0) return;

    const data = JSON.stringify(message);
    
    for (const client of clients) {
      if (client.readyState === 1) { // WebSocket.OPEN
        try {
          client.send(data);
        } catch (error) {
          logger.error('Failed to send to client', { error: error.message });
        }
      }
    }
  }

  /**
   * Get session info for API responses
   * @param {string} sessionId - Session identifier
   * @returns {object|null} Session info or null
   */
  getSessionInfo(sessionId) {
    const session = this.sessions.get(sessionId);
    if (!session) return null;

    return {
      session_id: session.sessionId,
      job_id: session.jobId,
      source: session.source,
      started_at: new Date(session.startedAt).toISOString(),
      frame_count: session.frameCount,
      screenshot_count: session.screenshotCount,
      current_url: session.currentUrl,
      is_active: session.isActive,
      num_viewers: this.wsClients.get(sessionId)?.size || 0
    };
  }

  /**
   * Get all active sessions
   * @returns {object[]} Array of session info objects
   */
  getActiveSessions() {
    const sessions = [];
    for (const sessionId of this.sessions.keys()) {
      const info = this.getSessionInfo(sessionId);
      if (info && info.is_active) {
        sessions.push(info);
      }
    }
    return sessions;
  }

  /**
   * Shutdown all sessions
   */
  async shutdown() {
    logger.info('Shutting down StreamManager...');
    
    for (const sessionId of this.sessions.keys()) {
      await this.stopScreencast(sessionId);
    }

    if (this.wss) {
      this.wss.close();
    }

    logger.info('StreamManager shutdown complete');
  }
}

// Singleton instance
let streamManagerInstance = null;

/**
 * Get or create StreamManager instance
 * @param {object} options - StreamManager options
 * @returns {StreamManager}
 */
export function getStreamManager(options = {}) {
  if (!streamManagerInstance) {
    streamManagerInstance = new StreamManager(options);
  }
  return streamManagerInstance;
}

export default StreamManager;
