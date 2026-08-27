import { useCallback, useEffect, useRef, useState } from 'react';
import { RealtimeChannel, RealtimeEventEnvelope, StreamStatus } from '../types/realtime';

export interface UseWebSocketStreamOptions {
  channel?: RealtimeChannel;
  path?: string;
  enabled?: boolean;
  heartbeatIntervalMs?: number;
  reconnectBaseDelayMs?: number;
  reconnectMaxDelayMs?: number;
  maxRetries?: number;
  onMessage?: (envelope: RealtimeEventEnvelope) => void;
  onSequenceGap?: (expected: number, received: number) => void;
  onStatusChange?: (status: StreamStatus) => void;
}

export interface WebSocketStreamState {
  status: StreamStatus;
  lastEvent: RealtimeEventEnvelope | null;
  lastSequence: number;
  latencyMs: number | null;
  error: string | null;
  connect: () => void;
  disconnect: () => void;
  sendPing: () => void;
}

export function resolveWebSocketUrl(path: string): string {
  if (typeof window === 'undefined') return `ws://localhost:8000${path}`;
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}${path}`;
}

export function useWebSocketStream(options: UseWebSocketStreamOptions = {}): WebSocketStreamState {
  const {
    channel = 'operational',
    path = `/api/v1/ws/${channel}`,
    enabled = true,
    heartbeatIntervalMs = 15000,
    reconnectBaseDelayMs = 1000,
    reconnectMaxDelayMs = 16000,
    maxRetries = 10,
    onMessage,
    onSequenceGap,
    onStatusChange,
  } = options;

  const [status, setStatus] = useState<StreamStatus>('DISCONNECTED');
  const [lastEvent, setLastEvent] = useState<RealtimeEventEnvelope | null>(null);
  const [lastSequence, setLastSequence] = useState<number>(0);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef<number>(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pingTimestampRef = useRef<number | null>(null);
  const isMountedRef = useRef<boolean>(true);

  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  const onSequenceGapRef = useRef(onSequenceGap);
  onSequenceGapRef.current = onSequenceGap;
  const onStatusChangeRef = useRef(onStatusChange);
  onStatusChangeRef.current = onStatusChange;

  const updateStatus = useCallback((newStatus: StreamStatus) => {
    if (!isMountedRef.current) return;
    setStatus(newStatus);
    if (onStatusChangeRef.current) {
      onStatusChangeRef.current(newStatus);
    }
  }, []);

  const sendPing = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      pingTimestampRef.current = Date.now();
      try {
        socketRef.current.send(
          JSON.stringify({
            type: 'ping',
            timestamp: new Date().toISOString(),
          })
        );
      } catch {
        // Socket error caught by onerror/onclose
      }
    }
  }, []);

  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
  }, []);

  const disconnect = useCallback(() => {
    clearTimers();
    retryCountRef.current = maxRetries; // Prevent auto-reconnect on deliberate disconnect
    if (socketRef.current) {
      try {
        socketRef.current.close(1000, 'Client disconnected');
      } catch {
        // Safe ignore
      }
      socketRef.current = null;
    }
    updateStatus('DISCONNECTED');
  }, [clearTimers, maxRetries, updateStatus]);

  const connect = useCallback(() => {
    if (!enabled) return;
    clearTimers();

    if (socketRef.current) {
      try {
        socketRef.current.close(1000, 'Reconnecting');
      } catch {
        // Safe ignore
      }
      socketRef.current = null;
    }

    const wsUrl = resolveWebSocketUrl(path);
    updateStatus(retryCountRef.current > 0 ? 'RECONNECTING' : 'CONNECTING');
    setError(null);

    try {
      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        if (!isMountedRef.current) return;
        retryCountRef.current = 0;
        updateStatus('CONNECTED');
        setError(null);

        // Start heartbeat interval
        if (heartbeatIntervalMs > 0) {
          heartbeatTimerRef.current = setInterval(sendPing, heartbeatIntervalMs);
        }
      };

      socket.onmessage = (event: MessageEvent) => {
        if (!isMountedRef.current) return;
        try {
          const envelope = JSON.parse(event.data) as RealtimeEventEnvelope;
          if (!envelope || typeof envelope !== 'object') return;

          // Check for heartbeat pong response
          if (
            envelope.event_type === 'system.heartbeat' &&
            envelope.payload &&
            (envelope.payload as { type?: string }).type === 'pong'
          ) {
            if (pingTimestampRef.current) {
              setLatencyMs(Date.now() - pingTimestampRef.current);
              pingTimestampRef.current = null;
            }
            return;
          }

          // Sequence continuity check
          if (typeof envelope.sequence === 'number') {
            setLastSequence((prevSeq) => {
              if (prevSeq > 0 && envelope.sequence > prevSeq + 1) {
                if (onSequenceGapRef.current) {
                  onSequenceGapRef.current(prevSeq + 1, envelope.sequence);
                }
              }
              return envelope.sequence;
            });
          }

          setLastEvent(envelope);
          if (onMessageRef.current) {
            onMessageRef.current(envelope);
          }
        } catch (err: unknown) {
          console.warn('[AeroGuard Realtime] Failed to parse WebSocket message:', err);
        }
      };

      socket.onerror = () => {
        if (!isMountedRef.current) return;
        setError('Realtime stream connection encountered an error.');
      };

      socket.onclose = (event: CloseEvent) => {
        if (!isMountedRef.current) return;
        clearTimers();
        socketRef.current = null;

        // If closed by policy violation or client disconnect, do not endlessly retry
        if (event.code === 1008 || event.code === 1000) {
          updateStatus('DISCONNECTED');
          if (event.reason) {
            setError(event.reason);
          }
          return;
        }

        // Exponential backoff reconnect
        if (retryCountRef.current < maxRetries) {
          const delay = Math.min(
            reconnectBaseDelayMs * Math.pow(1.5, retryCountRef.current) + Math.random() * 500,
            reconnectMaxDelayMs
          );
          retryCountRef.current += 1;
          updateStatus('RECONNECTING');
          reconnectTimerRef.current = setTimeout(connect, delay);
        } else {
          updateStatus('FAILED');
          setError('Maximum reconnection attempts reached. Operating in fallback mode.');
        }
      };
    } catch (err: unknown) {
      if (!isMountedRef.current) return;
      const msg = err instanceof Error ? err.message : 'Failed to instantiate WebSocket.';
      setError(msg);
      updateStatus('FAILED');
    }
  }, [
    clearTimers,
    enabled,
    heartbeatIntervalMs,
    maxRetries,
    path,
    reconnectBaseDelayMs,
    reconnectMaxDelayMs,
    sendPing,
    updateStatus,
  ]);

  useEffect(() => {
    isMountedRef.current = true;
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      isMountedRef.current = false;
      clearTimers();
      if (socketRef.current) {
        try {
          socketRef.current.close(1000, 'Component unmounted');
        } catch {
          // Safe ignore
        }
        socketRef.current = null;
      }
    };
  }, [connect, disconnect, clearTimers, enabled]);

  return {
    status,
    lastEvent,
    lastSequence,
    latencyMs,
    error,
    connect: () => {
      retryCountRef.current = 0;
      connect();
    },
    disconnect,
    sendPing,
  };
}
