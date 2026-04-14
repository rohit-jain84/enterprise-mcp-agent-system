import { useState, useEffect } from 'react';
import { Plus, Search, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useSessionStore } from '@/stores/sessionStore';
import { useChatStore } from '@/stores/chatStore';
import { apiClient } from '@/services/api';
import SessionItem from './SessionItem';
import LoadingSpinner from '@/components/common/LoadingSpinner';

export default function SessionSidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const {
    sessions,
    activeSession,
    isLoading,
    fetchSessions,
    createSession,
    deleteSession,
    setActiveSession,
  } = useSessionStore();
  const { setActiveSessionId, setMessages, clearMessages } = useChatStore();

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const filteredSessions = sessions.filter((s) =>
    (s.title || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleNewSession = async () => {
    try {
      const session = await createSession({ title: `Session ${sessions.length + 1}` });
      setActiveSessionId(session.id);
      clearMessages();
    } catch {
      // Error handled in store
    }
  };

  const handleSelectSession = async (session: typeof sessions[0]) => {
    setActiveSession(session);
    setActiveSessionId(session.id);
    try {
      const messages = await apiClient.getSessionMessages(session.id);
      setMessages(messages);
    } catch {
      setMessages([]);
    }
  };

  const handleDeleteSession = async (id: string) => {
    await deleteSession(id);
    if (activeSession?.id === id) {
      setActiveSessionId(null);
      clearMessages();
    }
  };

  if (collapsed) {
    return (
      <div className="w-12 bg-slate-800 border-r border-slate-700 flex flex-col items-center py-3 gap-2">
        <button
          onClick={() => setCollapsed(false)}
          className="p-2 hover:bg-slate-700 rounded-lg transition-colors text-slate-400 hover:text-slate-200"
          title="Expand sidebar"
        >
          <PanelLeftOpen size={18} />
        </button>
        <button
          onClick={handleNewSession}
          className="p-2 hover:bg-slate-700 rounded-lg transition-colors text-blue-400 hover:text-blue-300"
          title="New session"
        >
          <Plus size={18} />
        </button>
      </div>
    );
  }

  return (
    <div className="w-72 bg-slate-800 border-r border-slate-700 flex flex-col">
      <div className="p-3 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-200">Sessions</h2>
          <button
            onClick={() => setCollapsed(true)}
            className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors text-slate-400 hover:text-slate-200"
            title="Collapse sidebar"
          >
            <PanelLeftClose size={16} />
          </button>
        </div>

        <button
          onClick={handleNewSession}
          className="w-full flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors"
        >
          <Plus size={14} />
          New Session
        </button>

        <div className="relative mt-2">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search sessions..."
            className="w-full bg-slate-700 border border-slate-600 rounded-lg pl-9 pr-3 py-1.5 text-sm text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {isLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="sm" />
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="text-center py-8 text-sm text-slate-500">
            {searchQuery ? 'No sessions found' : 'No sessions yet'}
          </div>
        ) : (
          filteredSessions.map((session) => (
            <SessionItem
              key={session.id}
              session={session}
              isActive={activeSession?.id === session.id}
              onClick={() => handleSelectSession(session)}
              onDelete={() => handleDeleteSession(session.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}
