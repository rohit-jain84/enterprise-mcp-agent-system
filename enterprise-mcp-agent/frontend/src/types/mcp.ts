export interface MCPServer {
  id: string;
  name: string;
  url: string;
  status: 'connected' | 'disconnected' | 'error' | 'connecting';
  toolCount: number;
  lastHealthCheck?: string;
  version?: string;
  error?: string;
}

export interface MCPTool {
  name: string;
  description: string;
  server: string;
  inputSchema: Record<string, unknown>;
  requiresApproval: boolean;
}
