import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useState, useCallback } from 'react';
import { Copy, Check } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
}

function CodeBlock({ className, children }: { className?: string; children?: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || '');
  const language = match ? match[1] : '';
  const code = String(children).replace(/\n$/, '');

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [code]);

  if (!className) {
    return (
      <code className="bg-gray-100 text-cyan-700 dark:bg-slate-700 dark:text-cyan-300 px-1.5 py-0.5 rounded text-sm">
        {children}
      </code>
    );
  }

  return (
    <div className="relative group my-3">
      <div className="flex items-center justify-between bg-gray-200 dark:bg-slate-700 px-4 py-1.5 rounded-t-lg">
        <span className="text-xs text-gray-500 dark:text-slate-400 uppercase">{language}</span>
        <button
          onClick={handleCopy}
          className="text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 transition-colors p-1"
          title="Copy code"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
      </div>
      <pre className="bg-gray-100 border border-gray-200 border-t-0 dark:bg-slate-800 dark:border-slate-700 rounded-b-lg p-4 overflow-x-auto">
        <code className="text-sm text-gray-800 dark:text-slate-200">{code}</code>
      </pre>
    </div>
  );
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      className="prose prose-sm dark:prose-invert max-w-none
        prose-headings:text-gray-900 dark:prose-headings:text-slate-100
        prose-p:text-gray-700 dark:prose-p:text-slate-200 prose-p:leading-relaxed
        prose-a:text-blue-600 dark:prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline
        prose-strong:text-gray-900 dark:prose-strong:text-slate-100
        prose-ul:text-gray-700 dark:prose-ul:text-slate-200 prose-ol:text-gray-700 dark:prose-ol:text-slate-200
        prose-li:marker:text-gray-400 dark:prose-li:marker:text-slate-500
        prose-blockquote:border-blue-500 prose-blockquote:text-gray-600 dark:prose-blockquote:text-slate-300
        prose-hr:border-gray-200 dark:prose-hr:border-slate-700
        prose-table:text-gray-700 dark:prose-table:text-slate-200
        prose-th:text-gray-900 dark:prose-th:text-slate-100 prose-th:bg-gray-100 dark:prose-th:bg-slate-700/50 prose-th:px-3 prose-th:py-2
        prose-td:px-3 prose-td:py-2 prose-td:border-gray-200 dark:prose-td:border-slate-700"
      components={{
        code: ({ className, children }) => (
          <CodeBlock className={className}>{children}</CodeBlock>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
