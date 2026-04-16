import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}

export default function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="mb-4">{icon}</div>
      <h3 className="text-lg font-medium text-gray-600 dark:text-slate-300 mb-2">{title}</h3>
      <p className="text-sm text-gray-400 dark:text-slate-500 max-w-md mb-4">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
}
