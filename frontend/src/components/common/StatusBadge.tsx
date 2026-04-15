import clsx from 'clsx';

type BadgeStatus = 'connected' | 'disconnected' | 'connecting' | 'error' | 'pending' | 'approved' | 'rejected' | 'expired';

interface StatusBadgeProps {
  status: BadgeStatus;
  className?: string;
}

const statusStyles: Record<BadgeStatus, string> = {
  connected: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  disconnected: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  connecting: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  error: 'bg-red-500/20 text-red-400 border-red-500/30',
  pending: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  approved: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  rejected: 'bg-red-500/20 text-red-400 border-red-500/30',
  expired: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
};

const statusDot: Record<BadgeStatus, string> = {
  connected: 'bg-emerald-400',
  disconnected: 'bg-slate-400',
  connecting: 'bg-amber-400 animate-pulse',
  error: 'bg-red-400',
  pending: 'bg-amber-400 animate-pulse',
  approved: 'bg-emerald-400',
  rejected: 'bg-red-400',
  expired: 'bg-slate-400',
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border',
        statusStyles[status],
        className
      )}
    >
      <span className={clsx('w-1.5 h-1.5 rounded-full', statusDot[status])} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
