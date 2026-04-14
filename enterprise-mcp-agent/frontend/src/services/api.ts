import type { Session, SessionCreate } from '@/types/sessions';
import type { Approval } from '@/types/approvals';
import type { Message } from '@/types/messages';
import type { MCPServer } from '@/types/mcp';

const BASE_URL = '/api';

class TokenManager {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  setTokens(access: string, refresh: string) {
    this.accessToken = access;
    this.refreshToken = refresh;
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  getRefreshToken(): string | null {
    return this.refreshToken;
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }
}

const tokenManager = new TokenManager();

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers);
  const token = tokenManager.getAccessToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }

  let response = await fetch(url, { ...options, headers });

  if (response.status === 401 && tokenManager.getRefreshToken()) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      headers.set('Authorization', `Bearer ${tokenManager.getAccessToken()}`);
      response = await fetch(url, { ...options, headers });
    }
  }

  return response;
}

async function refreshAccessToken(): Promise<boolean> {
  try {
    const response = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: tokenManager.getRefreshToken() }),
    });
    if (response.ok) {
      const data = await response.json();
      tokenManager.setTokens(data.access_token, data.refresh_token);
      return true;
    }
    tokenManager.clearTokens();
    return false;
  } catch {
    tokenManager.clearTokens();
    return false;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API Error ${response.status}: ${errorBody}`);
  }
  return response.json();
}

export const apiClient = {
  // Auth
  async login(username: string, password: string): Promise<{ access_token: string; refresh_token: string }> {
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await handleResponse<{ access_token: string; refresh_token: string }>(response);
    tokenManager.setTokens(data.access_token, data.refresh_token);
    return data;
  },

  async refresh(): Promise<void> {
    await refreshAccessToken();
  },

  logout() {
    tokenManager.clearTokens();
  },

  getAccessToken(): string | null {
    return tokenManager.getAccessToken();
  },

  // Sessions
  async getSessions(): Promise<Session[]> {
    const response = await fetchWithAuth(`${BASE_URL}/sessions`);
    return handleResponse<Session[]>(response);
  },

  async getSession(id: string): Promise<Session> {
    const response = await fetchWithAuth(`${BASE_URL}/sessions/${id}`);
    return handleResponse<Session>(response);
  },

  async createSession(data?: SessionCreate): Promise<Session> {
    const response = await fetchWithAuth(`${BASE_URL}/sessions`, {
      method: 'POST',
      body: JSON.stringify(data || {}),
    });
    return handleResponse<Session>(response);
  },

  async deleteSession(id: string): Promise<void> {
    const response = await fetchWithAuth(`${BASE_URL}/sessions/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete session');
  },

  async getSessionMessages(sessionId: string): Promise<Message[]> {
    const response = await fetchWithAuth(`${BASE_URL}/sessions/${sessionId}/messages`);
    return handleResponse<Message[]>(response);
  },

  async sendMessage(sessionId: string, content: string): Promise<Message> {
    const response = await fetchWithAuth(`${BASE_URL}/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
    return handleResponse<Message>(response);
  },

  // Approvals
  async getApprovals(): Promise<Approval[]> {
    const response = await fetchWithAuth(`${BASE_URL}/approvals`);
    return handleResponse<Approval[]>(response);
  },

  async resolveApproval(id: string, action: 'approve' | 'reject', reason?: string): Promise<Approval> {
    const response = await fetchWithAuth(`${BASE_URL}/approvals/${id}`, {
      method: 'POST',
      body: JSON.stringify({ action, reason }),
    });
    return handleResponse<Approval>(response);
  },

  // Reports
  async getReports(): Promise<unknown> {
    const response = await fetchWithAuth(`${BASE_URL}/reports`);
    return handleResponse<unknown>(response);
  },

  // Health
  async getHealth(): Promise<{ status: string; servers: MCPServer[] }> {
    const response = await fetchWithAuth(`${BASE_URL}/health`);
    return handleResponse<{ status: string; servers: MCPServer[] }>(response);
  },

  async getMCPServers(): Promise<MCPServer[]> {
    const response = await fetchWithAuth(`${BASE_URL}/mcp/servers`);
    return handleResponse<MCPServer[]>(response);
  },
};
