import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Grid,
  List,
  Filter,
  Download,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Copy,
  Check,
  Image as ImageIcon,
  Radar,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { SearchInput } from '@/components/ui/Input'
import { Badge, StatusBadge } from '@/components/ui/Badge'
import { EmptyState } from '@/components/ui/EmptyState'
import { getAssets, getFilterOptions, reprocessAssets, type Asset } from '@/lib/api'
import { formatRelativeTime, formatSourceName, formatIndustryName, cn, truncate } from '@/lib/utils'

export default function Assets() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [view, setView] = useState<'grid' | 'list'>('grid')
  const [selectedAssets, setSelectedAssets] = useState<string[]>([])
  const [copiedPrompt, setCopiedPrompt] = useState<string | null>(null)
  const [filters, setFilters] = useState({
    industry: '',
    source: '',
    cta_type: '',
    has_prompt: '',
    search: '',
  })

  const { data: assets, isLoading } = useQuery({
    queryKey: ['assets', page, filters],
    queryFn: () => getAssets({
      page,
      page_size: view === 'grid' ? 12 : 20,
      industry: filters.industry || undefined,
      source: filters.source || undefined,
      cta_type: filters.cta_type || undefined,
      has_prompt: filters.has_prompt === 'true' ? true : filters.has_prompt === 'false' ? false : undefined,
      search: filters.search || undefined,
    }),
  })

  const { data: filterOptions } = useQuery({
    queryKey: ['filterOptions'],
    queryFn: getFilterOptions,
  })

  const reprocessMutation = useMutation({
    mutationFn: (assetIds: string[]) => reprocessAssets(assetIds, ['extract_features', 'generate_prompt']),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      setSelectedAssets([])
    },
  })

  const handleSelectAsset = (assetId: string) => {
    setSelectedAssets((prev) =>
      prev.includes(assetId)
        ? prev.filter((id) => id !== assetId)
        : [...prev, assetId]
    )
  }

  const copyPrompt = async (prompt: string, assetId: string) => {
    await navigator.clipboard.writeText(prompt)
    setCopiedPrompt(assetId)
    setTimeout(() => setCopiedPrompt(null), 2000)
  }

  const industryOptions = [
    { value: '', label: 'All Industries' },
    ...(filterOptions?.industries || []),
  ]

  const sourceOptions = [
    { value: '', label: 'All Sources' },
    ...(filterOptions?.sources || []),
  ]

  const ctaOptions = [
    { value: '', label: 'All CTA Types' },
    ...(filterOptions?.cta_types || []),
  ]

  const promptOptions = [
    { value: '', label: 'All Assets' },
    { value: 'true', label: 'With Prompt' },
    { value: 'false', label: 'Without Prompt' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Creative Assets</h1>
          <p className="text-surface-400 mt-1">
            Browse and manage scraped creative ads
          </p>
        </div>
        <div className="flex items-center gap-2">
          {selectedAssets.length > 0 && (
            <>
              <span className="text-sm text-surface-400">
                {selectedAssets.length} selected
              </span>
              <Button
                variant="secondary"
                onClick={() => reprocessMutation.mutate(selectedAssets)}
                loading={reprocessMutation.isPending}
              >
                <RefreshCw className="w-4 h-4" />
                Reprocess
              </Button>
            </>
          )}
          <Button variant="secondary">
            <Download className="w-4 h-4" />
            Export
          </Button>
          <div className="flex rounded-lg border border-surface-700 overflow-hidden">
            <button
              onClick={() => setView('grid')}
              className={cn(
                'p-2 transition-colors',
                view === 'grid' ? 'bg-surface-700 text-white' : 'text-surface-400 hover:text-white'
              )}
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setView('list')}
              className={cn(
                'p-2 transition-colors',
                view === 'list' ? 'bg-surface-700 text-white' : 'text-surface-400 hover:text-white'
              )}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <Select
              options={industryOptions}
              value={filters.industry}
              onChange={(e) => setFilters({ ...filters, industry: e.target.value })}
            />
            <Select
              options={sourceOptions}
              value={filters.source}
              onChange={(e) => setFilters({ ...filters, source: e.target.value })}
            />
            <Select
              options={ctaOptions}
              value={filters.cta_type}
              onChange={(e) => setFilters({ ...filters, cta_type: e.target.value })}
            />
            <Select
              options={promptOptions}
              value={filters.has_prompt}
              onChange={(e) => setFilters({ ...filters, has_prompt: e.target.value })}
            />
            <SearchInput
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              placeholder="Search assets..."
            />
          </div>
        </CardContent>
      </Card>

      {/* Assets Grid/List */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="card overflow-hidden">
              <div className="skeleton h-48" />
              <div className="p-4 space-y-2">
                <div className="skeleton h-4 w-3/4" />
                <div className="skeleton h-3 w-1/2" />
              </div>
            </div>
          ))}
        </div>
      ) : !assets?.assets || assets.assets.length === 0 ? (
        <Card>
          <CardContent className="py-16">
            <EmptyState
              icon={ImageIcon}
              title={filters.industry || filters.source || filters.search ? "No matching assets" : "No assets yet"}
              description={
                filters.industry || filters.source || filters.search
                  ? "Try adjusting your filters or search query"
                  : "Start by scraping some creative ads from the Scrapers page"
              }
              action={
                !filters.industry && !filters.source && !filters.search
                  ? {
                      label: 'Go to Scrapers',
                      onClick: () => window.location.href = '/scrapers',
                    }
                  : undefined
              }
            />
          </CardContent>
        </Card>
      ) : view === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {assets?.assets.map((asset) => (
            <AssetCard
              key={asset.id}
              asset={asset}
              selected={selectedAssets.includes(asset.id)}
              onSelect={() => handleSelectAsset(asset.id)}
              onCopyPrompt={() => asset.reverse_prompt && copyPrompt(asset.reverse_prompt, asset.id)}
              copied={copiedPrompt === asset.id}
            />
          ))}
        </div>
      ) : (
        <Card>
          <div className="divide-y divide-surface-800">
            {assets?.assets.map((asset) => (
              <AssetListItem
                key={asset.id}
                asset={asset}
                selected={selectedAssets.includes(asset.id)}
                onSelect={() => handleSelectAsset(asset.id)}
                onCopyPrompt={() => asset.reverse_prompt && copyPrompt(asset.reverse_prompt, asset.id)}
                copied={copiedPrompt === asset.id}
              />
            ))}
          </div>
        </Card>
      )}

      {/* Pagination */}
      {assets && assets.total > 12 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-surface-400">
            Showing {(page - 1) * (view === 'grid' ? 12 : 20) + 1} to{' '}
            {Math.min(page * (view === 'grid' ? 12 : 20), assets.total)} of {assets.total}
          </span>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="text-sm text-white px-3">Page {page}</span>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setPage((p) => p + 1)}
              disabled={!assets.has_more}
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function AssetCard({
  asset,
  selected,
  onSelect,
  onCopyPrompt,
  copied,
}: {
  asset: Asset
  selected: boolean
  onSelect: () => void
  onCopyPrompt: () => void
  copied: boolean
}) {
  return (
    <div
      className={cn(
        'card overflow-hidden group cursor-pointer transition-all',
        selected && 'ring-2 ring-brand-500'
      )}
      onClick={onSelect}
    >
      {/* Image */}
      <div className="relative h-48 bg-surface-800">
        {asset.image_url ? (
          <img
            src={asset.image_url}
            alt={asset.title || 'Creative asset'}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-surface-600">
            No image
          </div>
        )}
        
        {/* Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        
        {/* Checkbox */}
        <div className="absolute top-3 left-3">
          <div
            className={cn(
              'w-5 h-5 rounded border-2 flex items-center justify-center transition-colors',
              selected
                ? 'bg-brand-500 border-brand-500'
                : 'border-white/50 bg-black/30'
            )}
          >
            {selected && <Check className="w-3 h-3 text-white" />}
          </div>
        </div>

        {/* Industry badge */}
        {asset.industry && (
          <div className="absolute top-3 right-3">
            <Badge variant="info" size="sm">
              {formatIndustryName(asset.industry)}
            </Badge>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="font-medium text-white truncate">
          {asset.title || asset.advertiser_name || 'Untitled'}
        </h3>
        <p className="text-sm text-surface-400 mt-1">
          {formatSourceName(asset.source)} • {formatRelativeTime(asset.created_at)}
        </p>

        {/* Features */}
        <div className="flex flex-wrap gap-1 mt-3">
          {asset.features?.layout_type && (
            <Badge variant="neutral" size="sm">
              {asset.features.layout_type}
            </Badge>
          )}
          {asset.features?.cta?.type && (
            <Badge variant="neutral" size="sm">
              {asset.features.cta.type.replace(/_/g, ' ')}
            </Badge>
          )}
        </div>

        {/* Prompt preview */}
        {asset.reverse_prompt && (
          <div className="mt-3 pt-3 border-t border-surface-800">
            <div className="flex items-start justify-between gap-2">
              <p className="text-xs text-surface-400 line-clamp-2">
                {asset.reverse_prompt}
              </p>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onCopyPrompt()
                }}
                className="shrink-0 p-1 text-surface-400 hover:text-white"
              >
                {copied ? (
                  <Check className="w-4 h-4 text-success-500" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function AssetListItem({
  asset,
  selected,
  onSelect,
  onCopyPrompt,
  copied,
}: {
  asset: Asset
  selected: boolean
  onSelect: () => void
  onCopyPrompt: () => void
  copied: boolean
}) {
  return (
    <div
      className={cn(
        'flex items-center gap-4 p-4 hover:bg-surface-800/50 cursor-pointer transition-colors',
        selected && 'bg-brand-500/10'
      )}
      onClick={onSelect}
    >
      {/* Checkbox */}
      <div
        className={cn(
          'shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors',
          selected
            ? 'bg-brand-500 border-brand-500'
            : 'border-surface-600 bg-surface-800'
        )}
      >
        {selected && <Check className="w-3 h-3 text-white" />}
      </div>

      {/* Thumbnail */}
      <div className="shrink-0 w-16 h-16 rounded-lg overflow-hidden bg-surface-800">
        {asset.image_url ? (
          <img
            src={asset.image_url}
            alt=""
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="font-medium text-white truncate">
            {asset.title || asset.advertiser_name || 'Untitled'}
          </h3>
          {asset.industry && (
            <Badge variant="info" size="sm">
              {formatIndustryName(asset.industry)}
            </Badge>
          )}
        </div>
        <p className="text-sm text-surface-400 mt-1">
          {formatSourceName(asset.source)} • {formatRelativeTime(asset.created_at)}
        </p>
        {asset.reverse_prompt && (
          <p className="text-xs text-surface-500 mt-2 line-clamp-1">
            {asset.reverse_prompt}
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="shrink-0 flex items-center gap-2">
        {asset.reverse_prompt && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onCopyPrompt()
            }}
            className="p-2 text-surface-400 hover:text-white transition-colors"
          >
            {copied ? (
              <Check className="w-4 h-4 text-success-500" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
        )}
        {asset.source_url && (
          <a
            href={asset.source_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="p-2 text-surface-400 hover:text-white transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        )}
      </div>
    </div>
  )
}

