import { create } from 'zustand';
import type { Approval, ApprovalAction } from '@/types/approvals';
import { apiClient } from '@/services/api';

interface ApprovalState {
  pendingApprovals: Approval[];
  allApprovals: Approval[];
  isLoading: boolean;
  error: string | null;

  fetchApprovals: () => Promise<void>;
  addApproval: (approval: Approval) => void;
  approveAction: (action: ApprovalAction) => Promise<void>;
  rejectAction: (action: ApprovalAction) => Promise<void>;
  updateApproval: (id: string, updates: Partial<Approval>) => void;
  pendingCount: () => number;
}

export const useApprovalStore = create<ApprovalState>((set, get) => ({
  pendingApprovals: [],
  allApprovals: [],
  isLoading: false,
  error: null,

  fetchApprovals: async () => {
    set({ isLoading: true, error: null });
    try {
      const approvals = await apiClient.getApprovals();
      set({
        allApprovals: approvals,
        pendingApprovals: approvals.filter((a) => a.status === 'pending'),
        isLoading: false,
      });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },

  addApproval: (approval) =>
    set((state) => ({
      allApprovals: [approval, ...state.allApprovals],
      pendingApprovals:
        approval.status === 'pending'
          ? [approval, ...state.pendingApprovals]
          : state.pendingApprovals,
    })),

  approveAction: async (action) => {
    try {
      await apiClient.resolveApproval(action.approvalId, 'approve', action.reason);
      set((state) => ({
        pendingApprovals: state.pendingApprovals.filter(
          (a) => a.id !== action.approvalId
        ),
        allApprovals: state.allApprovals.map((a) =>
          a.id === action.approvalId
            ? { ...a, status: 'approved' as const, resolvedAt: new Date().toISOString() }
            : a
        ),
      }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  rejectAction: async (action) => {
    try {
      await apiClient.resolveApproval(action.approvalId, 'reject', action.reason);
      set((state) => ({
        pendingApprovals: state.pendingApprovals.filter(
          (a) => a.id !== action.approvalId
        ),
        allApprovals: state.allApprovals.map((a) =>
          a.id === action.approvalId
            ? { ...a, status: 'rejected' as const, resolvedAt: new Date().toISOString() }
            : a
        ),
      }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  updateApproval: (id, updates) =>
    set((state) => ({
      allApprovals: state.allApprovals.map((a) =>
        a.id === id ? { ...a, ...updates } : a
      ),
      pendingApprovals: state.pendingApprovals
        .map((a) => (a.id === id ? { ...a, ...updates } : a))
        .filter((a) => a.status === 'pending'),
    })),

  pendingCount: () => get().pendingApprovals.length,
}));
