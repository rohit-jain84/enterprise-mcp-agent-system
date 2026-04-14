import { useState } from 'react';
import clsx from 'clsx';
import ApprovalList from '@/components/approvals/ApprovalList';
import { useApprovalStore } from '@/stores/approvalStore';

export default function ApprovalQueuePage() {
  const [filter, setFilter] = useState<'pending' | 'all'>('pending');
  const pendingCount = useApprovalStore((s) => s.pendingApprovals.length);

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-100 mb-1">Approval Queue</h1>
          <p className="text-sm text-slate-400">
            Review and manage tool execution approval requests across all sessions.
          </p>
        </div>

        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setFilter('pending')}
            className={clsx(
              'px-4 py-2 text-sm rounded-lg transition-colors',
              filter === 'pending'
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                : 'bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700'
            )}
          >
            Pending
            {pendingCount > 0 && (
              <span className="ml-2 bg-amber-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                {pendingCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setFilter('all')}
            className={clsx(
              'px-4 py-2 text-sm rounded-lg transition-colors',
              filter === 'all'
                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                : 'bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700'
            )}
          >
            All
          </button>
        </div>

        <ApprovalList filter={filter} />
      </div>
    </div>
  );
}
