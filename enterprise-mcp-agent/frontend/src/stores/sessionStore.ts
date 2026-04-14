import { create } from 'zustand';
import type { Session, SessionCreate } from '@/types/sessions';
import { apiClient } from '@/services/api';

interface SessionState {
  sessions: Session[];
  activeSession: Session | null;
  isLoading: boolean;
  error: string | null;

  fetchSessions: () => Promise<void>;
  createSession: (data?: SessionCreate) => Promise<Session>;
  deleteSession: (id: string) => Promise<void>;
  setActiveSession: (session: Session | null) => void;
  updateSession: (id: string, updates: Partial<Session>) => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions: [],
  activeSession: null,
  isLoading: false,
  error: null,

  fetchSessions: async () => {
    set({ isLoading: true, error: null });
    try {
      const sessions = await apiClient.getSessions();
      set({ sessions, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },

  createSession: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const session = await apiClient.createSession(data);
      set((state) => ({
        sessions: [session, ...state.sessions],
        activeSession: session,
        isLoading: false,
      }));
      return session;
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
      throw err;
    }
  },

  deleteSession: async (id) => {
    try {
      await apiClient.deleteSession(id);
      set((state) => ({
        sessions: state.sessions.filter((s) => s.id !== id),
        activeSession:
          state.activeSession?.id === id ? null : state.activeSession,
      }));
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  setActiveSession: (session) => set({ activeSession: session }),

  updateSession: (id, updates) =>
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === id ? { ...s, ...updates } : s
      ),
      activeSession:
        state.activeSession?.id === id
          ? { ...state.activeSession, ...updates }
          : state.activeSession,
    })),
}));
