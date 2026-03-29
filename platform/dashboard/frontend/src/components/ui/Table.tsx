import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

interface TableProps {
  children: ReactNode;
  className?: string;
}

export function Table({ children, className }: TableProps) {
  return (
    <div className="overflow-x-auto">
      <table className={cn('w-full', className)}>{children}</table>
    </div>
  );
}

export function TableHead({ children, className }: { children: ReactNode; className?: string }) {
  return <thead className={cn('', className)}>{children}</thead>;
}

export function TableBody({ children, className }: { children: ReactNode; className?: string }) {
  return <tbody className={cn('', className)}>{children}</tbody>;
}

export function TableRow({
  children,
  className,
  onClick,
  selected
}: {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  selected?: boolean;
}) {
  return (
    <tr
      className={cn(
        'hover:bg-surface-800/50 transition-colors',
        onClick && 'cursor-pointer',
        selected && 'bg-brand-500/10',
        className
      )}
      onClick={onClick}
    >
      {children}
    </tr>
  );
}

export function TableHeader({
  children,
  className,
  align = 'left'
}: {
  children: ReactNode;
  className?: string;
  align?: 'left' | 'center' | 'right';
}) {
  return (
    <th
      className={cn(
        'px-4 py-3 text-xs font-semibold text-surface-400 uppercase tracking-wider bg-surface-900',
        align === 'center' && 'text-center',
        align === 'right' && 'text-right',
        className
      )}
    >
      {children}
    </th>
  );
}

export function TableCell({
  children,
  className,
  align = 'left'
}: {
  children: ReactNode;
  className?: string;
  align?: 'left' | 'center' | 'right';
}) {
  return (
    <td
      className={cn(
        'px-4 py-3 text-sm border-b border-surface-800',
        align === 'center' && 'text-center',
        align === 'right' && 'text-right',
        className
      )}
    >
      {children}
    </td>
  );
}

export function TableEmpty({ message = 'No data available' }: { message?: string }) {
  return (
    <tr>
      <td colSpan={100} className="px-4 py-12 text-center text-surface-500">
        {message}
      </td>
    </tr>
  );
}

export function TableLoading({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i}>
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} className="px-4 py-3 border-b border-surface-800">
              <div className="skeleton h-4 w-full" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
