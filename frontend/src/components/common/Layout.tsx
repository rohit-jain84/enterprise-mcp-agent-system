import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { MessageSquare, ShieldCheck, History, Settings, Zap, LogOut, Sun, Moon } from 'lucide-react';
import clsx from 'clsx';
import { useConnectionStore } from '@/stores/connectionStore';
import { useApprovalStore } from '@/stores/approvalStore';
import { useAuthStore } from '@/stores/authStore';
import { useTheme } from '@/context/ThemeContext';
import StatusBadge from './StatusBadge';

interface LayoutProps {
  children: ReactNode;
}

const navItems = [
  { to: '/', icon: MessageSquare, label: 'Chat' },
  { to: '/approvals', icon: ShieldCheck, label: 'Approvals' },
  { to: '/history', icon: History, label: 'History' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Layout({ children }: LayoutProps) {
  const { wsStatus } = useConnectionStore();
  const pendingCount = useApprovalStore((s) => s.pendingApprovals.length);
  const logout = useAuthStore((s) => s.logout);
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-slate-900">
      <header className="h-14 bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700 flex items-center justify-between px-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Zap size={20} className="text-cyan-500 dark:text-cyan-400" />
            <span className="font-semibold text-sm text-gradient">
              Enterprise MCP Agent
            </span>
          </div>

          <nav className="hidden md:flex items-center gap-1 ml-6">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors relative',
                    isActive
                      ? 'bg-blue-50 text-blue-700 dark:bg-slate-700 dark:text-white'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700/50'
                  )
                }
              >
                <item.icon size={16} />
                {item.label}
                {item.to === '/approvals' && pendingCount > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-amber-500 text-white text-xs rounded-full flex items-center justify-center font-bold">
                    {pendingCount}
                  </span>
                )}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <StatusBadge status={wsStatus} />
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700 transition-colors"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button
            onClick={logout}
            className="flex items-center gap-1.5 text-gray-500 hover:text-gray-700 dark:text-slate-400 dark:hover:text-slate-200 text-sm transition-colors"
            title="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </header>

      <main className="flex-1 min-h-0">{children}</main>

      {/* Mobile nav */}
      <nav className="md:hidden flex items-center justify-around bg-white dark:bg-slate-800 border-t border-gray-200 dark:border-slate-700 py-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg text-xs transition-colors relative',
                isActive
                  ? 'text-blue-600 dark:text-blue-400'
                  : 'text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-300'
              )
            }
          >
            <item.icon size={18} />
            {item.label}
            {item.to === '/approvals' && pendingCount > 0 && (
              <span className="absolute -top-1 right-0 w-4 h-4 bg-amber-500 text-white text-xs rounded-full flex items-center justify-center font-bold">
                {pendingCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
