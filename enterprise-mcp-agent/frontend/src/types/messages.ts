export type MessageRole = 'user' | 'assistant' | 'system';

export interface ToolCall {
  id: string;
  name: string;
  server: string;
  parameters: Record<string, unknown>;
  status: 'pending' | 'running' | 'completed' | 'failed';
  startedAt?: string;
  completedAt?: string;
}

export interface ToolResult {
  toolCallId: string;
  result: unknown;
  error?: string;
  duration?: number;
}

export interface Message {
  id: string;
  sessionId: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  toolCalls?: ToolCall[];
  toolResults?: ToolResult[];
  approvalId?: string;
  isStreaming?: boolean;
}

export type StreamEventType =
  | 'stream_start'
  | 'stream_chunk'
  | 'stream_end'
  | 'tool_call'
  | 'tool_result'
  | 'approval_request'
  | 'error';

export interface StreamEvent {
  type: StreamEventType;
  sessionId: string;
  data: StreamStartData | StreamChunkData | StreamEndData | ToolCallEventData | ToolResultEventData | ApprovalRequestData | ErrorData;
}

export interface StreamStartData {
  messageId: string;
}

export interface StreamChunkData {
  messageId: string;
  content: string;
}

export interface StreamEndData {
  messageId: string;
  fullContent: string;
}

export interface ToolCallEventData {
  toolCall: ToolCall;
  messageId: string;
}

export interface ToolResultEventData {
  toolResult: ToolResult;
  messageId: string;
}

export interface ApprovalRequestData {
  approvalId: string;
  toolCall: ToolCall;
  reason: string;
  messageId: string;
}

export interface ErrorData {
  message: string;
  code?: string;
}
