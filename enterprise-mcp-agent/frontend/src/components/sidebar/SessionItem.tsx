import { MessageSquare, Trash2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';
import type { Session } from '@/types/sessions';

interface SessionItemProps {
  session: Session;
  isActive: boolean;
  onClick: () => void;
  onDelete: () => void;
}

export default function SessionItem({ session, isActive, onClick, onDelete }: SessionItemProps) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full text-left px-3 py-2.5 rounded-lg transition-colors group',
        isActive
          ? 'bg-blue-600/20 border border-blue-500/30 text-blue-100'
          : 'hover:bg-slate-700/50 text-slate-300'
      )}
    >
      <div className="flex items-start gap-2">
        <MessageSquare
          size={14}
          className={clsx(
            'flex-shrink-0 mt-1',
            isActive ? 'text-blue-400' : 'text-slate-500'
          )}
        />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium truncate">
            {session.title || 'Untitled Session'}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-slate-500">
              {formatDistanceToNow(new Date(session.updatedAt), { addSuffix: true })}
            </span>
            <span className="text-xs text-slate-600">
              {session.messageCount} msgs
            </span>
          </div>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="flex-shrink-0 opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/20 rounded transition-all"
          title="Delete session"
        >
          <Trash2 size={12} className="text-red-400" />
        </button>
      </div>
    </button>
  );
}
