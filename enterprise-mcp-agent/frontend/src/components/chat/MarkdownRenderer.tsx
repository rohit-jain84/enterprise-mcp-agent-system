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
      <code className="bg-slate-700 text-cyan-300 px-1.5 py-0.5 rounded text-sm">
        {children}
      </code>
    );
  }

  return (
    <div className="relative group my-3">
      <div className="flex items-center justify-between bg-slate-700 px-4 py-1.5 rounded-t-lg">
        <span className="text-xs text-slate-400 uppercase">{language}</span>
        <button
          onClick={handleCopy}
          className="text-slate-400 hover:text-slate-200 transition-colors p-1"
          title="Copy code"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
      </div>
      <pre className="bg-slate-800 border border-slate-700 border-t-0 rounded-b-lg p-4 overflow-x-auto">
        <code className="text-sm text-slate-200">{code}</code>
      </pre>
    </div>
  );
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      className="prose prose-invert prose-sm max-w-none
        prose-headings:text-slate-100
        prose-p:text-slate-200 prose-p:leading-relaxed
        prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline
        prose-strong:text-slate-100
        prose-ul:text-slate-200 prose-ol:text-slate-200
        prose-li:marker:text-slate-500
        prose-blockquote:border-blue-500 prose-blockquote:text-slate-300
        prose-hr:border-slate-700
        prose-table:text-slate-200
        prose-th:text-slate-100 prose-th:bg-slate-700/50 prose-th:px-3 prose-th:py-2
        prose-td:px-3 prose-td:py-2 prose-td:border-slate-700"
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
