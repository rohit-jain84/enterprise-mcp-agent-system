import { useState } from 'react';
import { ChevronDown, ChevronRight, Wrench, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import clsx from 'clsx';
import type { ToolCall, ToolResult } from '@/types/messages';

interface ToolCallCardProps {
  toolCall: ToolCall;
  result?: ToolResult;
}

const SERVER_COLORS: Record<string, string> = {
  filesystem: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  database: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  api: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  search: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  default: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
};

function getServerColor(server: string): string {
  return SERVER_COLORS[server.toLowerCase()] || SERVER_COLORS.default;
}

export default function ToolCallCard({ toolCall, result }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);

  const isPending = toolCall.status === 'pending' || toolCall.status === 'running';
  const isFailed = toolCall.status === 'failed' || !!result?.error;

  return (
    <div
      className={clsx(
        'my-2 border rounded-lg overflow-hidden',
        isFailed
          ? 'border-red-300 bg-red-50 dark:border-red-500/30 dark:bg-red-500/5'
          : 'border-gray-200 bg-gray-50 dark:border-slate-600 dark:bg-slate-800/50'
      )}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-3 py-2 hover:bg-gray-100 dark:hover:bg-slate-700/30 transition-colors"
      >
        <div className="flex-shrink-0">
          {isPending ? (
            <Loader2 size={16} className="text-blue-500 dark:text-blue-400 animate-spin" />
          ) : isFailed ? (
            <XCircle size={16} className="text-red-500 dark:text-red-400" />
          ) : (
            <CheckCircle2 size={16} className="text-emerald-500 dark:text-emerald-400" />
          )}
        </div>

        <Wrench size={14} className="text-gray-400 dark:text-slate-400 flex-shrink-0" />
        <span className="text-sm font-mono text-gray-800 dark:text-slate-200">{toolCall.name}</span>

        <span
          className={clsx(
            'text-xs px-2 py-0.5 rounded-full border',
            getServerColor(toolCall.server)
          )}
        >
          {toolCall.server}
        </span>

        <div className="ml-auto flex-shrink-0">
          {expanded ? (
            <ChevronDown size={14} className="text-gray-400 dark:text-slate-400" />
          ) : (
            <ChevronRight size={14} className="text-gray-400 dark:text-slate-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t border-gray-200 dark:border-slate-700">
          <div className="pt-2">
            <div className="text-xs text-gray-500 dark:text-slate-400 mb-1">Parameters</div>
            <pre className="text-xs bg-gray-100 dark:bg-slate-900 rounded p-2 overflow-x-auto text-gray-600 dark:text-slate-300">
              {JSON.stringify(toolCall.parameters, null, 2)}
            </pre>
          </div>

          {result && (
            <div>
              <div className="text-xs text-gray-500 dark:text-slate-400 mb-1">
                {result.error ? 'Error' : 'Result'}
                {result.duration != null && (
                  <span className="ml-2 text-gray-400 dark:text-slate-500">({result.duration}ms)</span>
                )}
              </div>
              <pre
                className={clsx(
                  'text-xs rounded p-2 overflow-x-auto',
                  result.error
                    ? 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-300'
                    : 'bg-gray-100 text-gray-600 dark:bg-slate-900 dark:text-slate-300'
                )}
              >
                {result.error || JSON.stringify(result.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
