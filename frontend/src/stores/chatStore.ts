import { create } from 'zustand';
import type { Message, ToolCall, ToolResult } from '@/types/messages';

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  currentStreamContent: string;
  currentStreamMessageId: string | null;
  activeSessionId: string | null;
  pendingToolCalls: Map<string, ToolCall>;

  setActiveSessionId: (id: string | null) => void;
  addMessage: (message: Message) => void;
  setMessages: (messages: Message[]) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  startStream: (messageId: string) => void;
  updateStreamContent: (chunk: string) => void;
  endStream: (messageId: string, fullContent: string) => void;
  clearStream: () => void;
  addToolCall: (messageId: string, toolCall: ToolCall) => void;
  updateToolCall: (toolCallId: string, updates: Partial<ToolCall>) => void;
  addToolResult: (messageId: string, toolResult: ToolResult) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isStreaming: false,
  currentStreamContent: '',
  currentStreamMessageId: null,
  activeSessionId: null,
  pendingToolCalls: new Map(),

  setActiveSessionId: (id) => set({ activeSessionId: id }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  setMessages: (messages) => set({ messages }),

  updateMessage: (id, updates) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, ...updates } : m
      ),
    })),

  startStream: (messageId) =>
    set({
      isStreaming: true,
      currentStreamContent: '',
      currentStreamMessageId: messageId,
    }),

  updateStreamContent: (chunk) =>
    set((state) => ({
      currentStreamContent: state.currentStreamContent + chunk,
    })),

  endStream: (messageId, fullContent) => {
    const state = get();
    const existingMessage = state.messages.find((m) => m.id === messageId);
    if (existingMessage) {
      set((s) => ({
        isStreaming: false,
        currentStreamContent: '',
        currentStreamMessageId: null,
        messages: s.messages.map((m) =>
          m.id === messageId
            ? { ...m, content: fullContent, isStreaming: false }
            : m
        ),
      }));
    } else {
      set((s) => ({
        isStreaming: false,
        currentStreamContent: '',
        currentStreamMessageId: null,
        messages: [
          ...s.messages,
          {
            id: messageId,
            sessionId: s.activeSessionId || '',
            role: 'assistant',
            content: fullContent,
            timestamp: new Date().toISOString(),
            isStreaming: false,
          },
        ],
      }));
    }
  },

  clearStream: () =>
    set({
      isStreaming: false,
      currentStreamContent: '',
      currentStreamMessageId: null,
    }),

  addToolCall: (messageId, toolCall) => {
    set((state) => {
      const newPending = new Map(state.pendingToolCalls);
      newPending.set(toolCall.id, toolCall);
      return {
        pendingToolCalls: newPending,
        messages: state.messages.map((m) =>
          m.id === messageId
            ? { ...m, toolCalls: [...(m.toolCalls || []), toolCall] }
            : m
        ),
      };
    });
  },

  updateToolCall: (toolCallId, updates) =>
    set((state) => {
      const newPending = new Map(state.pendingToolCalls);
      const existing = newPending.get(toolCallId);
      if (existing) {
        newPending.set(toolCallId, { ...existing, ...updates });
      }
      return {
        pendingToolCalls: newPending,
        messages: state.messages.map((m) => ({
          ...m,
          toolCalls: m.toolCalls?.map((tc) =>
            tc.id === toolCallId ? { ...tc, ...updates } : tc
          ),
        })),
      };
    }),

  addToolResult: (messageId, toolResult) =>
    set((state) => {
      const newPending = new Map(state.pendingToolCalls);
      newPending.delete(toolResult.toolCallId);
      return {
        pendingToolCalls: newPending,
        messages: state.messages.map((m) =>
          m.id === messageId
            ? { ...m, toolResults: [...(m.toolResults || []), toolResult] }
            : m
        ),
      };
    }),

  clearMessages: () =>
    set({
      messages: [],
      isStreaming: false,
      currentStreamContent: '',
      currentStreamMessageId: null,
      pendingToolCalls: new Map(),
    }),
}));
