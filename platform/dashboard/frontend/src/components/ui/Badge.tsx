import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral';

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  dot?: boolean;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  success: 'bg-success-500/20 text-success-500',
  warning: 'bg-warning-500/20 text-warning-500',
  danger: 'bg-danger-500/20 text-danger-500',
  info: 'bg-brand-500/20 text-brand-400',
  neutral: 'bg-surface-700 text-surface-300'
};

const sizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm'
};

export function Badge({
  children,
  variant = 'neutral',
  size = 'sm',
  dot = false,
  className
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
    >
      {dot && (
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full',
            variant === 'success' && 'bg-success-500',
            variant === 'warning' && 'bg-warning-500',
            variant === 'danger' && 'bg-danger-500',
            variant === 'info' && 'bg-brand-500',
            variant === 'neutral' && 'bg-surface-400'
          )}
        />
      )}
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const statusVariants: Record<string, BadgeVariant> = {
    pending: 'warning',
    in_progress: 'info',
    running: 'info',
    completed: 'success',
    success: 'success',
    failed: 'danger',
    error: 'danger',
    retrying: 'warning',
    paused: 'neutral',
    cancelled: 'neutral'
  };

  const variant = statusVariants[status.toLowerCase()] || 'neutral';
  const displayStatus = status.replace(/_/g, ' ');

  return (
    <Badge variant={variant} dot>
      {displayStatus}
    </Badge>
  );
}
