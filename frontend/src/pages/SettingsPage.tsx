import { useEffect, useState } from 'react';
import { Server, RefreshCw, Wrench, Activity } from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import { apiClient } from '@/services/api';
import type { MCPServer } from '@/types/mcp';
import StatusBadge from '@/components/common/StatusBadge';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import EmptyState from '@/components/common/EmptyState';

export default function SettingsPage() {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchServers = async () => {
    try {
      const data = await apiClient.getMCPServers();
      setServers(data);
    } catch {
      // Use mock data for display
      setServers([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchServers();
    setRefreshing(false);
  };

  const totalTools = servers.reduce((sum, s) => sum + s.toolCount, 0);
  const connectedCount = servers.filter((s) => s.status === 'connected').length;

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-100 mb-1">Settings</h1>
            <p className="text-sm text-slate-400">
              MCP server connections and system configuration.
            </p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw size={14} className={clsx(refreshing && 'animate-spin')} />
            Refresh
          </button>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <div className="card">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                <Server size={20} className="text-blue-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-slate-100">{servers.length}</div>
                <div className="text-xs text-slate-400">Total Servers</div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
                <Activity size={20} className="text-emerald-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-slate-100">{connectedCount}</div>
                <div className="text-xs text-slate-400">Connected</div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center">
                <Wrench size={20} className="text-purple-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-slate-100">{totalTools}</div>
                <div className="text-xs text-slate-400">Available Tools</div>
              </div>
            </div>
          </div>
        </div>

        <h2 className="text-lg font-semibold text-slate-200 mb-4">MCP Servers</h2>

        {loading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner />
          </div>
        ) : servers.length === 0 ? (
          <EmptyState
            icon={<Server size={48} className="text-slate-500" />}
            title="No MCP servers configured"
            description="MCP server connections will appear here once the backend is running."
          />
        ) : (
          <div className="space-y-3">
            {servers.map((server) => (
              <div key={server.id} className="card">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div
                      className={clsx(
                        'w-10 h-10 rounded-lg flex items-center justify-center',
                        server.status === 'connected'
                          ? 'bg-emerald-500/20'
                          : server.status === 'error'
                          ? 'bg-red-500/20'
                          : 'bg-slate-700'
                      )}
                    >
                      <Server
                        size={20}
                        className={clsx(
                          server.status === 'connected'
                            ? 'text-emerald-400'
                            : server.status === 'error'
                            ? 'text-red-400'
                            : 'text-slate-400'
                        )}
                      />
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-slate-200">
                        {server.name}
                      </h3>
                      <p className="text-xs text-slate-500 font-mono">{server.url}</p>
                    </div>
                  </div>

                  <StatusBadge status={server.status} />
                </div>

                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <span className="flex items-center gap-1">
                    <Wrench size={12} />
                    {server.toolCount} tools
                  </span>
                  {server.version && <span>v{server.version}</span>}
                  {server.lastHealthCheck && (
                    <span>
                      Last check:{' '}
                      {format(new Date(server.lastHealthCheck), 'HH:mm:ss')}
                    </span>
                  )}
                </div>

                {server.error && (
                  <div className="mt-2 text-xs text-red-400 bg-red-500/10 rounded-lg p-2">
                    {server.error}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
