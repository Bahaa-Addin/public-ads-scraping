import { LucideIcon, Inbox } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
  size = 'md',
}: EmptyStateProps) {
  const sizes = {
    sm: {
      icon: 'w-8 h-8',
      iconWrapper: 'w-14 h-14',
      title: 'text-sm',
      description: 'text-xs',
      padding: 'py-6',
    },
    md: {
      icon: 'w-10 h-10',
      iconWrapper: 'w-20 h-20',
      title: 'text-base',
      description: 'text-sm',
      padding: 'py-12',
    },
    lg: {
      icon: 'w-12 h-12',
      iconWrapper: 'w-24 h-24',
      title: 'text-lg',
      description: 'text-base',
      padding: 'py-16',
    },
  }

  const s = sizes[size]

  return (
    <div className={cn('flex flex-col items-center justify-center text-center', s.padding, className)}>
      <div className={cn('rounded-full bg-surface-800/50 flex items-center justify-center mb-4', s.iconWrapper)}>
        <Icon className={cn('text-surface-500', s.icon)} />
      </div>
      <h3 className={cn('font-medium text-surface-300 mb-1', s.title)}>{title}</h3>
      {description && (
        <p className={cn('text-surface-500 max-w-sm', s.description)}>{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-500 transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}

// Quick variants for common empty states
export function NoDataYet({ message = 'No data yet', description }: { message?: string; description?: string }) {
  return <EmptyState title={message} description={description} size="sm" />
}

export function EmptyList({ 
  itemName = 'items',
  description,
}: { 
  itemName?: string
  description?: string
}) {
  return (
    <EmptyState
      title={`No ${itemName} found`}
      description={description || `There are no ${itemName} to display at this time.`}
    />
  )
}

