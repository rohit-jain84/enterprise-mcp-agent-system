import { useEffect } from 'react';
import { useApprovalStore } from '@/stores/approvalStore';
import ApprovalItem from './ApprovalItem';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import EmptyState from '@/components/common/EmptyState';
import { ShieldCheck } from 'lucide-react';

interface ApprovalListProps {
  filter?: 'pending' | 'all';
}

export default function ApprovalList({ filter = 'all' }: ApprovalListProps) {
  const { pendingApprovals, allApprovals, isLoading, fetchApprovals } =
    useApprovalStore();

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  const approvals = filter === 'pending' ? pendingApprovals : allApprovals;

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner />
      </div>
    );
  }

  if (approvals.length === 0) {
    return (
      <EmptyState
        icon={<ShieldCheck size={48} className="text-slate-500" />}
        title={filter === 'pending' ? 'No pending approvals' : 'No approvals yet'}
        description={
          filter === 'pending'
            ? 'All tool calls have been resolved. New approval requests will appear here.'
            : 'Approval requests from MCP tool calls will appear here.'
        }
      />
    );
  }

  return (
    <div className="space-y-3">
      {approvals.map((approval) => (
        <ApprovalItem key={approval.id} approval={approval} />
      ))}
    </div>
  );
}
