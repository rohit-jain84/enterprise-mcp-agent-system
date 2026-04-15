import type { Session, SessionCreate } from '@/types/sessions';
import type { Approval } from '@/types/approvals';
import type { Message } from '@/types/messages';
import type { MCPServer } from '@/types/mcp';

const BASE_URL = '/api/v1';

/* eslint-disable @typescript-eslint/no-explicit-any */
function mapSession(raw: any): Session {
  return {
    id: raw.id,
    title: raw.title || 'New Chat',
    createdAt: raw.created_at || raw.createdAt,
    updatedAt: raw.updated_at || raw.updatedAt,
    messageCount: raw.message_count ?? raw.messageCount ?? 0,
    status: raw.status || 'active',
    summary: raw.summary,
    tags: raw.tags,
  };
}

function mapApproval(raw: any): Approval {
  return {
    id: raw.id,
    sessionId: raw.session_id || raw.sessionId,
    toolCall: raw.toolCall || {
      id: raw.id,
      name: raw.tool_name || raw.toolName || '',
      server: 'unknown',
      parameters: raw.tool_args || raw.toolArgs || {},
      status: raw.status === 'pending' ? 'pending' : 'completed',
    },
    reason: raw.reason || '',
    status: raw.status,
    createdAt: raw.created_at || raw.createdAt,
    resolvedAt: raw.responded_at || raw.respondedAt,
    resolvedBy: raw.responded_by || raw.respondedBy,
  };
}

function mapMessage(raw: any): Message {
  return {
    id: raw.id,
    sessionId: raw.session_id || raw.sessionId,
    role: raw.role,
    content: raw.content,
    timestamp: raw.created_at || raw.createdAt || raw.timestamp,
    toolCalls: raw.tool_calls || raw.toolCalls,
    toolResults: raw.tool_results || raw.toolResults,
  };
}
/* eslint-enable @typescript-eslint/no-explicit-any */

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
  async login(email: string, password: string): Promise<{ access_token: string; refresh_token: string }> {
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
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
    const raw = await handleResponse<any[]>(response);
    return raw.map(mapSession);
  },

  async getSession(id: string): Promise<Session> {
    const response = await fetchWithAuth(`${BASE_URL}/sessions/${id}`);
    const raw = await handleResponse<any>(response);
    return mapSession(raw);
  },

  async createSession(data?: SessionCreate): Promise<Session> {
    const response = await fetchWithAuth(`${BASE_URL}/sessions`, {
      method: 'POST',
      body: JSON.stringify(data || {}),
    });
    const raw = await handleResponse<any>(response);
    return mapSession(raw);
  },

  async deleteSession(id: string): Promise<void> {
    const response = await fetchWithAuth(`${BASE_URL}/sessions/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete session');
  },

  async getSessionMessages(sessionId: string): Promise<Message[]> {
    const response = await fetchWithAuth(`${BASE_URL}/sessions/${sessionId}/messages`);
    const raw = await handleResponse<any[]>(response);
    return raw.map(mapMessage);
  },

  async sendMessage(sessionId: string, content: string): Promise<Message> {
    const response = await fetchWithAuth(`${BASE_URL}/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
    const raw = await handleResponse<any>(response);
    return mapMessage(raw);
  },

  // Approvals
  async getApprovals(): Promise<Approval[]> {
    const response = await fetchWithAuth(`${BASE_URL}/approvals`);
    const raw = await handleResponse<any[]>(response);
    return raw.map(mapApproval);
  },

  async resolveApproval(id: string, action: 'approve' | 'reject', reason?: string): Promise<Approval> {
    const response = await fetchWithAuth(`${BASE_URL}/approvals/${id}`, {
      method: 'POST',
      body: JSON.stringify({ action, reason }),
    });
    const raw = await handleResponse<any>(response);
    return mapApproval(raw);
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
