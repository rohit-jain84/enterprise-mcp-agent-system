import { useState } from 'react';
import { Zap, LogIn, Sun, Moon } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { useTheme } from '@/context/ThemeContext';

export default function LoginPage() {
  const { login, isLoading, error } = useAuthStore();
  const { theme, toggleTheme } = useTheme();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login(email, password);
    } catch {
      // error is set in store
    }
  };

  return (
    <div className="h-screen flex items-center justify-center bg-gray-50 dark:bg-slate-900 relative">
      <button
        onClick={toggleTheme}
        className="absolute top-4 right-4 p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700 transition-colors"
        title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      >
        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
      </button>

      <div className="w-full max-w-md px-6">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-3">
            <Zap size={32} className="text-cyan-500 dark:text-cyan-400" />
            <h1 className="text-2xl font-bold text-gradient">
              Enterprise MCP Agent
            </h1>
          </div>
          <p className="text-sm text-gray-500 dark:text-slate-400">
            Sign in to access the agent dashboard
          </p>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 dark:bg-red-500/10 dark:border-red-500/30 rounded-lg px-3 py-2 text-sm text-red-600 dark:text-red-400">
              Invalid email or password
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-white border border-gray-300 dark:bg-slate-800 dark:border-slate-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-slate-100 placeholder-gray-400 dark:placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="admin@acme.com"
              required
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-white border border-gray-300 dark:bg-slate-800 dark:border-slate-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-slate-100 placeholder-gray-400 dark:placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="Enter password"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 text-white font-medium py-2.5 px-4 rounded-lg text-sm transition-colors"
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <LogIn size={16} />
            )}
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>

          <p className="text-xs text-gray-400 dark:text-slate-500 text-center">
            Demo: admin@acme.com / admin123
          </p>
        </form>
      </div>
    </div>
  );
}
