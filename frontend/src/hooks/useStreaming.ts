import { useChatStore } from '@/stores/chatStore';

export function useStreaming() {
  const {
    isStreaming,
    currentStreamContent,
    currentStreamMessageId,
    messages,
  } = useChatStore();

  const streamingMessage = isStreaming && currentStreamMessageId
    ? {
        id: currentStreamMessageId,
        role: 'assistant' as const,
        content: currentStreamContent,
        timestamp: new Date().toISOString(),
        sessionId: '',
        isStreaming: true,
      }
    : null;

  const displayMessages = streamingMessage
    ? [...messages.filter((m) => m.id !== currentStreamMessageId), streamingMessage]
    : messages;

  return {
    isStreaming,
    currentStreamContent,
    streamingMessage,
    displayMessages,
  };
}
