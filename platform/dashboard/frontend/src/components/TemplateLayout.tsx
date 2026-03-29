import { Outlet, NavLink, useLocation, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  LayoutDashboard,
  ListTodo,
  Image,
  Radar,
  BarChart3,
  FileText,
  Settings,
  Activity,
  AlertCircle,
  CheckCircle,
  Bell,
  Menu,
  X,
  Home,
  FlaskConical,
  Play
} from 'lucide-react';
import { useState } from 'react';
import { getHealth } from '@/lib/api';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/template/dashboard', icon: LayoutDashboard },
  { name: 'Pipeline', href: '/template/pipeline', icon: Play },
  { name: 'Jobs', href: '/template/jobs', icon: ListTodo },
  { name: 'Assets', href: '/template/assets', icon: Image },
  { name: 'Scrapers', href: '/template/scrapers', icon: Radar },
  { name: 'Analytics', href: '/template/analytics', icon: BarChart3 },
  { name: 'Logs', href: '/template/logs', icon: FileText },
  { name: 'Settings', href: '/template/settings', icon: Settings }
];

export default function TemplateLayout() {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30000
  });

  const isHealthy = health?.status === 'healthy';

  return (
    <div className="min-h-screen bg-surface-950">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed top-0 left-0 z-50 h-full w-64 bg-surface-900 border-r border-surface-800 transform transition-transform duration-200 ease-in-out lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-surface-800">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-cyan-500 flex items-center justify-center">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-white">Agentic Ads</h1>
            <p className="text-xs text-surface-400">Pipeline Dashboard</p>
          </div>
        </div>

        {/* Template Badge */}
        <div className="mx-3 mt-4 mb-2 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
          <div className="flex items-center gap-2 text-amber-500">
            <FlaskConical className="w-4 h-4" />
            <span className="text-xs font-medium">Template Mode</span>
          </div>
          <p className="text-xs text-amber-500/70 mt-1">Using mock data</p>
        </div>

        {/* Navigation */}
        <nav className="px-3 py-4 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname.startsWith(item.href);
            return (
              <NavLink
                key={item.name}
                to={item.href}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'bg-brand-500/20 text-brand-400'
                    : 'text-surface-400 hover:text-white hover:bg-surface-800'
                )}
              >
                <item.icon className="w-5 h-5" />
                {item.name}
              </NavLink>
            );
          })}
        </nav>

        {/* Back to Home */}
        <div className="px-3 mt-4">
          <Link
            to="/"
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-surface-500 hover:text-white hover:bg-surface-800 transition-all duration-200"
          >
            <Home className="w-5 h-5" />
            Back to Home
          </Link>
        </div>

        {/* System Status */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-surface-800">
          <div className="card p-3">
            <div className="flex items-center gap-2 mb-2">
              {isHealthy ? (
                <CheckCircle className="w-4 h-4 text-success-500" />
              ) : (
                <AlertCircle className="w-4 h-4 text-warning-500" />
              )}
              <span className="text-xs font-medium text-surface-300">System Status</span>
            </div>
            <p
              className={cn(
                'text-sm font-semibold',
                isHealthy ? 'text-success-500' : 'text-warning-500'
              )}
            >
              {isHealthy ? 'All Systems Operational' : 'Partial Degradation'}
            </p>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-30 flex items-center justify-between px-4 lg:px-6 py-4 bg-surface-950/80 backdrop-blur-xl border-b border-surface-800">
          {/* Mobile menu button */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="lg:hidden p-2 -ml-2 text-surface-400 hover:text-white"
          >
            {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>

          {/* Page title */}
          <div className="hidden lg:flex items-center gap-3">
            <h2 className="text-lg font-semibold text-white capitalize">
              {location.pathname.split('/').pop() || 'Dashboard'}
            </h2>
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-500/10 text-amber-500 border border-amber-500/20">
              Mock Data
            </span>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-4">
            {/* Status indicator */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-800 text-xs">
              <span
                className={cn(
                  'w-2 h-2 rounded-full',
                  isHealthy ? 'bg-success-500 animate-pulse' : 'bg-warning-500'
                )}
              />
              <span className="text-surface-300">{isHealthy ? 'Connected' : 'Degraded'}</span>
            </div>

            {/* Notifications */}
            <button className="relative p-2 text-surface-400 hover:text-white transition-colors">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-danger-500 rounded-full" />
            </button>

            {/* User avatar */}
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-purple-500 flex items-center justify-center text-white text-sm font-medium">
              A
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
