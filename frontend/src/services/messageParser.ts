import type {
  StreamEvent,
  StreamEventType,
  StreamStartData,
  StreamChunkData,
  StreamEndData,
  ToolCallEventData,
  ToolResultEventData,
  ApprovalRequestData,
  ErrorData,
} from '@/types/messages';

export function parseStreamEvent(raw: unknown): StreamEvent | null {
  if (!raw || typeof raw !== 'object') return null;

  const obj = raw as Record<string, unknown>;
  const type = obj.type as StreamEventType;
  const sessionId = (obj.sessionId || obj.session_id) as string;
  const data = obj.data as Record<string, unknown>;

  if (!type || !data) return null;

  switch (type) {
    case 'stream_start':
      return {
        type,
        sessionId,
        data: {
          messageId: data.messageId || data.message_id,
        } as StreamStartData,
      };

    case 'stream_chunk':
      return {
        type,
        sessionId,
        data: {
          messageId: data.messageId || data.message_id,
          content: data.content,
        } as StreamChunkData,
      };

    case 'stream_end':
      return {
        type,
        sessionId,
        data: {
          messageId: data.messageId || data.message_id,
          fullContent: data.fullContent || data.full_content,
        } as StreamEndData,
      };

    case 'tool_call':
      return {
        type,
        sessionId,
        data: {
          toolCall: data.toolCall || data.tool_call,
          messageId: data.messageId || data.message_id,
        } as ToolCallEventData,
      };

    case 'tool_result':
      return {
        type,
        sessionId,
        data: {
          toolResult: data.toolResult || data.tool_result,
          messageId: data.messageId || data.message_id,
        } as ToolResultEventData,
      };

    case 'approval_request':
      return {
        type,
        sessionId,
        data: {
          approvalId: data.approvalId || data.approval_id,
          toolCall: data.toolCall || data.tool_call,
          reason: data.reason,
          messageId: data.messageId || data.message_id,
        } as ApprovalRequestData,
      };

    case 'error':
      return {
        type,
        sessionId,
        data: {
          message: data.message,
          code: data.code,
        } as ErrorData,
      };

    default:
      console.warn('Unknown stream event type:', type);
      return null;
  }
}
