import { useState } from 'react';
import { ShieldAlert, Check, X, Clock, ChevronDown, ChevronRight } from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import type { Approval } from '@/types/approvals';
import { useApprovalStore } from '@/stores/approvalStore';
import StatusBadge from '@/components/common/StatusBadge';

interface ApprovalItemProps {
  approval: Approval;
}

export default function ApprovalItem({ approval }: ApprovalItemProps) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const { approveAction, rejectAction } = useApprovalStore();
  const isPending = approval.status === 'pending';

  const handleApprove = async () => {
    setLoading(true);
    try {
      await approveAction({ approvalId: approval.id, action: 'approve' });
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    try {
      await rejectAction({ approvalId: approval.id, action: 'reject' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={clsx(
        'border rounded-xl p-4 transition-colors',
        isPending
          ? 'border-amber-300 bg-amber-50 dark:border-amber-500/40 dark:bg-amber-500/5'
          : 'border-gray-200 bg-white dark:border-slate-700 dark:bg-slate-800/50'
      )}
    >
      <div className="flex items-start gap-3">
        <ShieldAlert
          size={20}
          className={clsx(
            'flex-shrink-0 mt-0.5',
            isPending ? 'text-amber-500 dark:text-amber-400' : 'text-gray-400 dark:text-slate-500'
          )}
        />

        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-sm text-gray-800 dark:text-slate-200">
              {approval.toolCall.name}
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30">
              {approval.toolCall.server}
            </span>
            <StatusBadge status={approval.status} />
          </div>

          <p className="text-sm text-gray-600 dark:text-slate-300 mb-2">{approval.reason}</p>

          <div className="flex items-center gap-3 text-xs text-gray-400 dark:text-slate-500 mb-2">
            <span className="flex items-center gap-1">
              <Clock size={12} />
              {format(new Date(approval.createdAt), 'MMM d, HH:mm')}
            </span>
            <span>Session: {approval.sessionId.slice(0, 8)}...</span>
          </div>

          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300 transition-colors mb-2"
          >
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            Parameters
          </button>

          {expanded && (
            <pre className="text-xs bg-gray-100 dark:bg-slate-900 rounded-lg p-3 overflow-x-auto text-gray-500 dark:text-slate-400 mb-3">
              {JSON.stringify(approval.toolCall.parameters, null, 2)}
            </pre>
          )}

          {isPending && (
            <div className="flex gap-2">
              <button
                onClick={handleApprove}
                disabled={loading}
                className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
              >
                <Check size={14} />
                Approve
              </button>
              <button
                onClick={handleReject}
                disabled={loading}
                className="flex items-center gap-1.5 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
              >
                <X size={14} />
                Reject
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
