import SessionSidebar from '@/components/sidebar/SessionSidebar';
import ChatContainer from '@/components/chat/ChatContainer';

export default function ChatPage() {
  return (
    <div className="flex h-full">
      <SessionSidebar />
      <ChatContainer />
    </div>
  );
}
