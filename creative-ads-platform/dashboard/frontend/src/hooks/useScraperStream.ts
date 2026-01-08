/**
 * useScraperStream - WebSocket hook for live scraper video streaming
 * 
 * Connects to the agent's WebSocket endpoint to receive real-time
 * video frames from an active scraper session.
 */

import { useState, useEffect, useRef, useCallback } from 'react'

export type StreamStatus = 'connecting' | 'connected' | 'waiting' | 'live' | 'ended' | 'disconnected' | 'error'

interface StreamFrame {
  data: string  // Base64 JPEG data
  timestamp: string
  metadata?: {
    deviceWidth?: number
    deviceHeight?: number
    pageScaleFactor?: number
    scrollOffsetX?: number
    scrollOffsetY?: number
  }
}

interface SessionInfo {
  session_id: string
  job_id: string
  source: string
  started_at: string
  frame_count: number
  screenshot_count: number
  current_url?: string
  is_active: boolean
}

interface UseScraperStreamOptions {
  /** Auto-reconnect on disconnect (default: true) */
  autoReconnect?: boolean
  /** Reconnection delay in ms (default: 2000) */
  reconnectDelay?: number
  /** Max reconnection attempts (default: 5) */
  maxReconnectAttempts?: number
  /** Ping interval in ms to keep connection alive (default: 30000) */
  pingInterval?: number
}

interface UseScraperStreamReturn {
  /** Current frame as data URL (data:image/jpeg;base64,...) */
  frame: string | null
  /** Raw base64 frame data */
  frameData: string | null
  /** Connection status */
  status: StreamStatus
  /** Session information */
  sessionInfo: SessionInfo | null
  /** Number of frames received */
  frameCount: number
  /** Error message if any */
  error: string | null
  /** Manually disconnect */
  disconnect: () => void
  /** Manually reconnect */
  reconnect: () => void
}

// Default to agent API port
const AGENT_WS_URL = import.meta.env.VITE_AGENT_WS_URL || 'ws://localhost:8080'

export function useScraperStream(
  sessionId: string | null,
  options: UseScraperStreamOptions = {}
): UseScraperStreamReturn {
  const {
    autoReconnect = true,
    reconnectDelay = 2000,
    maxReconnectAttempts = 5,
    pingInterval = 30000,
  } = options

  const [frame, setFrame] = useState<string | null>(null)
  const [frameData, setFrameData] = useState<string | null>(null)
  const [status, setStatus] = useState<StreamStatus>('disconnected')
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null)
  const [frameCount, setFrameCount] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const connect = useCallback(() => {
    if (!sessionId) {
      setStatus('disconnected')
      return
    }

    cleanup()
    setStatus('connecting')
    setError(null)

    try {
      const ws = new WebSocket(`${AGENT_WS_URL}/ws/scraper/${sessionId}`)
      wsRef.current = ws

      ws.onopen = () => {
        setStatus('connected')
        reconnectAttemptsRef.current = 0
        
        // Start ping interval to keep connection alive
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, pingInterval)
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          
          switch (message.type) {
            case 'session_info':
              setSessionInfo(message.session)
              setStatus('live')
              break
              
            case 'waiting':
              setStatus('waiting')
              break
              
            case 'frame':
              setFrameData(message.data)
              setFrame(`data:image/jpeg;base64,${message.data}`)
              setFrameCount(c => c + 1)
              setStatus('live')
              break
              
            case 'stream_ended':
              setStatus('ended')
              setSessionInfo(prev => prev ? { ...prev, is_active: false } : null)
              break
              
            default:
              // Unknown message type
              break
          }
        } catch (e) {
          // Handle text messages (like pong)
          if (event.data === 'pong') {
            // Connection is alive
          }
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        setError('WebSocket connection error')
        setStatus('error')
      }

      ws.onclose = (event) => {
        cleanup()
        
        if (event.code === 1000 || event.code === 1001) {
          // Normal closure
          setStatus('disconnected')
        } else if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          // Attempt reconnection
          setStatus('connecting')
          reconnectAttemptsRef.current++
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectDelay * Math.pow(1.5, reconnectAttemptsRef.current - 1))
        } else {
          setStatus('disconnected')
          if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
            setError('Max reconnection attempts reached')
          }
        }
      }
    } catch (e) {
      console.error('Failed to create WebSocket:', e)
      setError('Failed to create WebSocket connection')
      setStatus('error')
    }
  }, [sessionId, autoReconnect, reconnectDelay, maxReconnectAttempts, pingInterval, cleanup])

  const disconnect = useCallback(() => {
    reconnectAttemptsRef.current = maxReconnectAttempts // Prevent auto-reconnect
    cleanup()
    setStatus('disconnected')
  }, [cleanup, maxReconnectAttempts])

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0
    connect()
  }, [connect])

  // Connect when sessionId changes
  useEffect(() => {
    if (sessionId) {
      connect()
    } else {
      cleanup()
      setStatus('disconnected')
      setFrame(null)
      setFrameData(null)
      setSessionInfo(null)
      setFrameCount(0)
    }

    return cleanup
  }, [sessionId, connect, cleanup])

  return {
    frame,
    frameData,
    status,
    sessionInfo,
    frameCount,
    error,
    disconnect,
    reconnect,
  }
}

// Dashboard API for fetching active scrapers
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Hook to get list of active scraper sessions
 */
export function useActiveScrapers(pollInterval = 5000) {
  const [sessions, setSessions] = useState<SessionInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchActiveSessions = async () => {
      try {
        // Use dashboard backend which proxies to agent
        const response = await fetch(`${API_URL}/api/v1/scrapers/active`)
        if (!response.ok) throw new Error('Failed to fetch active scrapers')
        const data = await response.json()
        setSessions(data.sessions || [])
        setError(null)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to fetch')
      } finally {
        setLoading(false)
      }
    }

    fetchActiveSessions()
    const interval = setInterval(fetchActiveSessions, pollInterval)

    return () => clearInterval(interval)
  }, [pollInterval])

  return { sessions, loading, error }
}
