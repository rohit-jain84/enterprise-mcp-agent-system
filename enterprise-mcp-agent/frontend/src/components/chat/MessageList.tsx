import type { Message } from '@/types/messages';
import MessageBubble from './MessageBubble';

interface MessageListProps {
  messages: Message[];
}

export default function MessageList({ messages }: MessageListProps) {
  return (
    <div className="flex flex-col gap-1 py-4">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
    </div>
  );
}
