import { cn, formatNumber } from '@/lib/utils';
import { TrendingUp, TrendingDown } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: number | string;
  icon: LucideIcon;
  change?: number;
  changeLabel?: string;
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'cyan';
  loading?: boolean;
}

const colorClasses = {
  blue: {
    bg: 'bg-blue-500/20',
    text: 'text-blue-400',
    icon: 'text-blue-500'
  },
  green: {
    bg: 'bg-green-500/20',
    text: 'text-green-400',
    icon: 'text-green-500'
  },
  yellow: {
    bg: 'bg-yellow-500/20',
    text: 'text-yellow-400',
    icon: 'text-yellow-500'
  },
  red: {
    bg: 'bg-red-500/20',
    text: 'text-red-400',
    icon: 'text-red-500'
  },
  purple: {
    bg: 'bg-purple-500/20',
    text: 'text-purple-400',
    icon: 'text-purple-500'
  },
  cyan: {
    bg: 'bg-cyan-500/20',
    text: 'text-cyan-400',
    icon: 'text-cyan-500'
  }
};

export function StatCard({
  title,
  value,
  icon: Icon,
  change,
  changeLabel,
  color = 'blue',
  loading = false
}: StatCardProps) {
  const classes = colorClasses[color];

  if (loading) {
    return (
      <div className="card p-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="skeleton h-4 w-24 mb-2" />
            <div className="skeleton h-8 w-20" />
          </div>
          <div className="skeleton w-12 h-12 rounded-xl" />
        </div>
      </div>
    );
  }

  const formattedValue = typeof value === 'number' ? formatNumber(value) : value;

  return (
    <div className="card p-5 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-surface-400 font-medium">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{formattedValue}</p>

          {change !== undefined && (
            <div className="flex items-center gap-1 mt-2">
              {change >= 0 ? (
                <TrendingUp className="w-4 h-4 text-success-500" />
              ) : (
                <TrendingDown className="w-4 h-4 text-danger-500" />
              )}
              <span
                className={cn(
                  'text-sm font-medium',
                  change >= 0 ? 'text-success-500' : 'text-danger-500'
                )}
              >
                {change >= 0 ? '+' : ''}
                {change.toFixed(1)}%
              </span>
              {changeLabel && <span className="text-xs text-surface-500">{changeLabel}</span>}
            </div>
          )}
        </div>

        <div className={cn('p-3 rounded-xl', classes.bg)}>
          <Icon className={cn('w-6 h-6', classes.icon)} />
        </div>
      </div>
    </div>
  );
}
