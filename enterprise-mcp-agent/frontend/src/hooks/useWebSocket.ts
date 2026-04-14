import { useEffect, useRef, useCallback } from 'react';
import { wsService } from '@/services/websocket';
import { parseStreamEvent } from '@/services/messageParser';
import { useChatStore } from '@/stores/chatStore';
import { useApprovalStore } from '@/stores/approvalStore';
import { useConnectionStore } from '@/stores/connectionStore';
import type {
  StreamChunkData,
  StreamEndData,
  StreamStartData,
  ToolCallEventData,
  ToolResultEventData,
  ApprovalRequestData,
  ErrorData,
  StreamEvent,
} from '@/types/messages';

export function useWebSocket(sessionId: string | null) {
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { startStream, updateStreamContent, endStream, addToolCall, addToolResult, addMessage } =
    useChatStore();
  const { addApproval } = useApprovalStore();
  const {
    setWsStatus,
    reconnectAttempts,
    maxReconnectAttempts,
    incrementReconnectAttempts,
    resetReconnectAttempts,
  } = useConnectionStore();

  const handleMessage = useCallback(
    (event: StreamEvent) => {
      const parsed = parseStreamEvent(event);
      if (!parsed) return;

      switch (parsed.type) {
        case 'stream_start': {
          const d = parsed.data as StreamStartData;
          startStream(d.messageId);
          break;
        }
        case 'stream_chunk': {
          const d = parsed.data as StreamChunkData;
          updateStreamContent(d.content);
          break;
        }
        case 'stream_end': {
          const d = parsed.data as StreamEndData;
          endStream(d.messageId, d.fullContent);
          break;
        }
        case 'tool_call': {
          const d = parsed.data as ToolCallEventData;
          addToolCall(d.messageId, d.toolCall);
          break;
        }
        case 'tool_result': {
          const d = parsed.data as ToolResultEventData;
          addToolResult(d.messageId, d.toolResult);
          break;
        }
        case 'approval_request': {
          const d = parsed.data as ApprovalRequestData;
          addApproval({
            id: d.approvalId,
            sessionId: parsed.sessionId,
            toolCall: d.toolCall,
            reason: d.reason,
            status: 'pending',
            createdAt: new Date().toISOString(),
          });
          break;
        }
        case 'error': {
          const d = parsed.data as ErrorData;
          addMessage({
            id: `error-${Date.now()}`,
            sessionId: parsed.sessionId,
            role: 'system',
            content: `Error: ${d.message}`,
            timestamp: new Date().toISOString(),
          });
          break;
        }
      }
    },
    [startStream, updateStreamContent, endStream, addToolCall, addToolResult, addApproval, addMessage]
  );

  const connect = useCallback(() => {
    if (!sessionId) return;

    const token = localStorage.getItem('access_token') || undefined;
    wsService.connect(sessionId, token);
  }, [sessionId]);

  const scheduleReconnect = useCallback(() => {
    if (reconnectAttempts >= maxReconnectAttempts) {
      setWsStatus('error');
      return;
    }

    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
    reconnectTimerRef.current = setTimeout(() => {
      incrementReconnectAttempts();
      connect();
    }, delay);
  }, [reconnectAttempts, maxReconnectAttempts, connect, incrementReconnectAttempts, setWsStatus]);

  useEffect(() => {
    if (!sessionId) {
      wsService.disconnect();
      setWsStatus('disconnected');
      return;
    }

    const unsubMessage = wsService.onMessage(handleMessage);
    const unsubStatus = wsService.onStatus((status) => {
      setWsStatus(status);

      if (status === 'connected') {
        resetReconnectAttempts();
      } else if (status === 'disconnected' && wsService.getShouldReconnect()) {
        scheduleReconnect();
      }
    });

    connect();

    return () => {
      unsubMessage();
      unsubStatus();
      wsService.disconnect();
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, [sessionId, connect, handleMessage, scheduleReconnect, setWsStatus, resetReconnectAttempts]);

  const sendMessage = useCallback(
    (content: string) => {
      wsService.send({ type: 'message', content });
    },
    []
  );

  return { sendMessage };
}
