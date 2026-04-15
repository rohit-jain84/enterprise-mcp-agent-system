import { create } from 'zustand';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface MCPServerHealth {
  serverId: string;
  name: string;
  status: ConnectionStatus;
  lastCheck: string;
  toolCount: number;
  error?: string;
}

interface ConnectionState {
  wsStatus: ConnectionStatus;
  mcpServers: Map<string, MCPServerHealth>;
  reconnectAttempts: number;
  maxReconnectAttempts: number;

  setWsStatus: (status: ConnectionStatus) => void;
  setMCPServerHealth: (serverId: string, health: MCPServerHealth) => void;
  removeMCPServer: (serverId: string) => void;
  incrementReconnectAttempts: () => void;
  resetReconnectAttempts: () => void;
  setMCPServers: (servers: Map<string, MCPServerHealth>) => void;
}

export const useConnectionStore = create<ConnectionState>((set) => ({
  wsStatus: 'disconnected',
  mcpServers: new Map(),
  reconnectAttempts: 0,
  maxReconnectAttempts: 10,

  setWsStatus: (status) => set({ wsStatus: status }),

  setMCPServerHealth: (serverId, health) =>
    set((state) => {
      const newMap = new Map(state.mcpServers);
      newMap.set(serverId, health);
      return { mcpServers: newMap };
    }),

  removeMCPServer: (serverId) =>
    set((state) => {
      const newMap = new Map(state.mcpServers);
      newMap.delete(serverId);
      return { mcpServers: newMap };
    }),

  incrementReconnectAttempts: () =>
    set((state) => ({
      reconnectAttempts: state.reconnectAttempts + 1,
    })),

  resetReconnectAttempts: () => set({ reconnectAttempts: 0 }),

  setMCPServers: (servers) => set({ mcpServers: servers }),
}));
