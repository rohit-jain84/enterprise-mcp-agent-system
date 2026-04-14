import type { ToolCall } from './messages';

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired';

export interface Approval {
  id: string;
  sessionId: string;
  toolCall: ToolCall;
  reason: string;
  status: ApprovalStatus;
  createdAt: string;
  resolvedAt?: string;
  resolvedBy?: string;
}

export interface ApprovalAction {
  approvalId: string;
  action: 'approve' | 'reject';
  reason?: string;
}
