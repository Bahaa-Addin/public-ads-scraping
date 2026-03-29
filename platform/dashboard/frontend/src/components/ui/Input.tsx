import { cn } from '@/lib/utils';
import { forwardRef } from 'react';
import type { InputHTMLAttributes } from 'react';
import { Search } from 'lucide-react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, icon, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-surface-300 mb-1.5">{label}</label>
        )}
        <div className="relative">
          {icon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500">{icon}</div>
          )}
          <input
            ref={ref}
            className={cn(
              'w-full px-4 py-2.5 bg-surface-900 border border-surface-700 rounded-lg',
              'text-white placeholder-surface-500',
              'focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500',
              'transition-all duration-200',
              icon && 'pl-10',
              error && 'border-danger-500 focus:ring-danger-500/50 focus:border-danger-500',
              className
            )}
            {...props}
          />
        </div>
        {error && <p className="mt-1.5 text-sm text-danger-500">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';

export function SearchInput({ className, ...props }: InputProps) {
  return (
    <Input
      icon={<Search className="w-4 h-4" />}
      placeholder="Search..."
      className={className}
      {...props}
    />
  );
}
