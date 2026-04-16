import { useState } from 'react';
import { ShieldAlert, Check, X } from 'lucide-react';
import clsx from 'clsx';
import { useApprovalStore } from '@/stores/approvalStore';
import type { ApprovalStatus } from '@/types/approvals';
import type { ToolCall } from '@/types/messages';
import StatusBadge from '@/components/common/StatusBadge';

interface ApprovalCardProps {
  approvalId: string;
  toolCall: ToolCall;
  reason: string;
  status: ApprovalStatus;
}

export default function ApprovalCard({ approvalId, toolCall, reason, status }: ApprovalCardProps) {
  const [loading, setLoading] = useState(false);
  const { approveAction, rejectAction } = useApprovalStore();

  const isPending = status === 'pending';

  const handleApprove = async () => {
    setLoading(true);
    try {
      await approveAction({ approvalId, action: 'approve' });
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    try {
      await rejectAction({ approvalId, action: 'reject' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={clsx(
        'my-2 border rounded-lg p-3',
        isPending
          ? 'border-amber-300 bg-amber-50 dark:border-amber-500/40 dark:bg-amber-500/10'
          : status === 'approved'
          ? 'border-emerald-300 bg-emerald-50 dark:border-emerald-500/30 dark:bg-emerald-500/5'
          : status === 'rejected'
          ? 'border-red-300 bg-red-50 dark:border-red-500/30 dark:bg-red-500/5'
          : 'border-gray-200 bg-gray-50 dark:border-slate-600 dark:bg-slate-800/50'
      )}
    >
      <div className="flex items-start gap-3">
        <ShieldAlert
          size={18}
          className={clsx(
            'flex-shrink-0 mt-0.5',
            isPending ? 'text-amber-500 dark:text-amber-400' : 'text-gray-400 dark:text-slate-400'
          )}
        />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-gray-800 dark:text-slate-200">Approval Required</span>
            {!isPending && <StatusBadge status={status} />}
          </div>

          <p className="text-sm text-gray-600 dark:text-slate-300 mb-2">{reason}</p>

          <div className="text-xs text-gray-500 dark:text-slate-400 mb-2">
            <span className="font-mono">{toolCall.name}</span> on{' '}
            <span className="text-cyan-600 dark:text-cyan-400">{toolCall.server}</span>
          </div>

          <pre className="text-xs bg-gray-100 dark:bg-slate-900/50 rounded p-2 overflow-x-auto text-gray-500 dark:text-slate-400 mb-3">
            {JSON.stringify(toolCall.parameters, null, 2)}
          </pre>

          {isPending && (
            <div className="flex gap-2">
              <button
                onClick={handleApprove}
                disabled={loading}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
              >
                <Check size={14} />
                Approve
              </button>
              <button
                onClick={handleReject}
                disabled={loading}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
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
