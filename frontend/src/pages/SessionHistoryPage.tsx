import { useEffect, useState } from 'react';
import { Search, Calendar, MessageSquare, Archive } from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import { useSessionStore } from '@/stores/sessionStore';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import EmptyState from '@/components/common/EmptyState';
import StatusBadge from '@/components/common/StatusBadge';

type StatusFilter = 'all' | 'active' | 'completed' | 'archived';

export default function SessionHistoryPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const { sessions, isLoading, fetchSessions } = useSessionStore();

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const filteredSessions = sessions.filter((s) => {
    const matchesSearch =
      (s.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (s.summary || '').toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === 'all' || s.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statusFilters: { value: StatusFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'active', label: 'Active' },
    { value: 'completed', label: 'Completed' },
    { value: 'archived', label: 'Archived' },
  ];

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100 mb-1">Session History</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400">
            Browse and search through past agent sessions.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search sessions..."
              className="w-full bg-white border border-gray-300 dark:bg-slate-800 dark:border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-gray-800 dark:text-slate-200 placeholder-gray-400 dark:placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex gap-2">
            {statusFilters.map((f) => (
              <button
                key={f.value}
                onClick={() => setStatusFilter(f.value)}
                className={clsx(
                  'px-3 py-2 text-sm rounded-lg transition-colors',
                  statusFilter === f.value
                    ? 'bg-blue-50 text-blue-600 border border-blue-200 dark:bg-blue-500/20 dark:text-blue-400 dark:border-blue-500/30'
                    : 'bg-white text-gray-500 border border-gray-300 hover:bg-gray-50 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700 dark:hover:bg-slate-700'
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner />
          </div>
        ) : filteredSessions.length === 0 ? (
          <EmptyState
            icon={<Archive size={48} className="text-gray-400 dark:text-slate-500" />}
            title="No sessions found"
            description={
              searchQuery
                ? 'Try adjusting your search or filters.'
                : 'Session history will appear here after you start chatting.'
            }
          />
        ) : (
          <div className="space-y-3">
            {filteredSessions.map((session) => (
              <div
                key={session.id}
                className="card hover:border-gray-300 dark:hover:border-slate-600 transition-colors cursor-pointer"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-sm font-medium text-gray-800 dark:text-slate-200 truncate">
                        {session.title || 'Untitled Session'}
                      </h3>
                      <StatusBadge
                        status={
                          session.status === 'active'
                            ? 'connected'
                            : session.status === 'completed'
                            ? 'approved'
                            : 'disconnected'
                        }
                      />
                    </div>
                    {session.summary && (
                      <p className="text-xs text-gray-500 dark:text-slate-400 line-clamp-2">
                        {session.summary}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-4 text-xs text-gray-400 dark:text-slate-500">
                  <span className="flex items-center gap-1">
                    <Calendar size={12} />
                    {format(new Date(session.createdAt), 'MMM d, yyyy HH:mm')}
                  </span>
                  <span className="flex items-center gap-1">
                    <MessageSquare size={12} />
                    {session.messageCount} messages
                  </span>
                  {session.tags && session.tags.length > 0 && (
                    <div className="flex gap-1">
                      {session.tags.map((tag) => (
                        <span
                          key={tag}
                          className="px-1.5 py-0.5 bg-gray-100 dark:bg-slate-700 rounded text-gray-500 dark:text-slate-400"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
