import { User, Bot, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';
import { format } from 'date-fns';
import type { Message } from '@/types/messages';
import MarkdownRenderer from './MarkdownRenderer';
import ToolCallCard from './ToolCallCard';
import ApprovalCard from './ApprovalCard';
import { useApprovalStore } from '@/stores/approvalStore';

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const { allApprovals } = useApprovalStore();

  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  const approval = message.approvalId
    ? allApprovals.find((a) => a.id === message.approvalId)
    : null;

  return (
    <div
      className={clsx(
        'flex gap-3 px-4 py-3',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      <div
        className={clsx(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isUser
            ? 'bg-blue-600'
            : isSystem
            ? 'bg-amber-600'
            : 'bg-gradient-to-br from-cyan-500 to-purple-600'
        )}
      >
        {isUser ? (
          <User size={16} className="text-white" />
        ) : isSystem ? (
          <AlertTriangle size={16} className="text-white" />
        ) : (
          <Bot size={16} className="text-white" />
        )}
      </div>

      <div
        className={clsx(
          'flex-1 max-w-[80%] space-y-1',
          isUser ? 'items-end' : 'items-start'
        )}
      >
        <div
          className={clsx(
            'rounded-xl px-4 py-2.5',
            isUser
              ? 'bg-blue-600 text-white rounded-tr-sm'
              : isSystem
              ? 'bg-amber-900/30 border border-amber-700/40 text-amber-200 rounded-tl-sm'
              : 'bg-slate-800 border border-slate-700 text-slate-200 rounded-tl-sm'
          )}
        >
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <MarkdownRenderer content={message.content} />
          )}

          {message.isStreaming && (
            <span className="inline-block w-2 h-4 bg-cyan-400 animate-pulse ml-0.5" />
          )}
        </div>

        {message.toolCalls?.map((tc) => {
          const result = message.toolResults?.find(
            (tr) => tr.toolCallId === tc.id
          );
          return <ToolCallCard key={tc.id} toolCall={tc} result={result} />;
        })}

        {approval && (
          <ApprovalCard
            approvalId={approval.id}
            toolCall={approval.toolCall}
            reason={approval.reason}
            status={approval.status}
          />
        )}

        <div
          className={clsx(
            'text-xs text-slate-500 px-1',
            isUser ? 'text-right' : 'text-left'
          )}
        >
          {format(new Date(message.timestamp), 'HH:mm')}
        </div>
      </div>
    </div>
  );
}
