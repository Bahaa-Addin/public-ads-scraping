import { cn } from '@/lib/utils';
import { forwardRef } from 'react';
import type { SelectHTMLAttributes } from 'react';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  placeholder?: string;
  error?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, options, placeholder, error, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-surface-300 mb-1.5">{label}</label>
        )}
        <select
          ref={ref}
          className={cn(
            'w-full px-4 py-2.5 bg-surface-900 border border-surface-700 rounded-lg',
            'text-white appearance-none cursor-pointer',
            'focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500',
            'transition-all duration-200',
            error && 'border-danger-500',
            className
          )}
          style={{
            backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`,
            backgroundPosition: 'right 0.5rem center',
            backgroundRepeat: 'no-repeat',
            backgroundSize: '1.5em 1.5em',
            paddingRight: '2.5rem'
          }}
          {...props}
        >
          {placeholder && (
            <option value="" className="text-surface-500">
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {error && <p className="mt-1.5 text-sm text-danger-500">{error}</p>}
      </div>
    );
  }
);

Select.displayName = 'Select';
