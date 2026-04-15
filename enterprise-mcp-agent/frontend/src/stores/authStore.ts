import { create } from 'zustand';
import { apiClient } from '@/services/api';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      await apiClient.login(email, password);
      set({ isAuthenticated: true, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  logout: () => {
    apiClient.logout();
    set({ isAuthenticated: false });
  },

  checkAuth: () => {
    set({ isAuthenticated: !!apiClient.getAccessToken() });
  },
}));
