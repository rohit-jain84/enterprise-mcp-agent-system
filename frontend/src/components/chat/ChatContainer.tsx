import { useCallback } from 'react';
import { ArrowDown } from 'lucide-react';
import { useChatStore } from '@/stores/chatStore';
import { useStreaming } from '@/hooks/useStreaming';
import { useAutoScroll } from '@/hooks/useAutoScroll';
import { useWebSocket } from '@/hooks/useWebSocket';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import EmptyState from '@/components/common/EmptyState';
import { MessageSquare } from 'lucide-react';

export default function ChatContainer() {
  const { activeSessionId, addMessage } = useChatStore();
  const { isStreaming, displayMessages } = useStreaming();
  const { containerRef, scrollToBottom, isUserScrolled } = useAutoScroll([
    displayMessages,
  ]);
  const { sendMessage: wsSend } = useWebSocket(activeSessionId);

  const handleSend = useCallback(
    (content: string) => {
      if (!activeSessionId) return;

      addMessage({
        id: `user-${Date.now()}`,
        sessionId: activeSessionId,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      });

      wsSend(content);
    },
    [activeSessionId, addMessage, wsSend]
  );

  if (!activeSessionId) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <EmptyState
          icon={<MessageSquare size={48} className="text-gray-400 dark:text-slate-500" />}
          title="No session selected"
          description="Create a new session or select an existing one from the sidebar to start chatting."
        />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div ref={containerRef} className="flex-1 overflow-y-auto relative">
        {displayMessages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <EmptyState
              icon={<MessageSquare size={48} className="text-gray-400 dark:text-slate-500" />}
              title="Start a conversation"
              description="Send a message to begin interacting with the MCP agent."
            />
          </div>
        ) : (
          <MessageList messages={displayMessages} />
        )}

        {isUserScrolled && (
          <button
            onClick={scrollToBottom}
            className="sticky bottom-4 left-1/2 -translate-x-1/2 bg-white dark:bg-slate-700 hover:bg-gray-100 dark:hover:bg-slate-600 text-gray-600 dark:text-slate-300 rounded-full p-2 shadow-lg transition-colors"
          >
            <ArrowDown size={16} />
          </button>
        )}
      </div>

      <ChatInput onSend={handleSend} disabled={isStreaming} />
    </div>
  );
}
