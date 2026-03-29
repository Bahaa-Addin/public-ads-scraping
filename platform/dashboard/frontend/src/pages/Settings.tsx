import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Settings as SettingsIcon,
  Server,
  Database,
  Cloud,
  Bell,
  Palette,
  CheckCircle,
  XCircle,
  AlertCircle,
  ExternalLink
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { getHealth } from '@/lib/api';
import { cn, formatDuration } from '@/lib/utils';

export default function Settings() {
  const [activeTab, setActiveTab] = useState('general');

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30000
  });

  const tabs = [
    { id: 'general', label: 'General', icon: SettingsIcon },
    { id: 'services', label: 'Services', icon: Server },
    { id: 'storage', label: 'Storage', icon: Database },
    { id: 'gcp', label: 'GCP', icon: Cloud },
    { id: 'notifications', label: 'Notifications', icon: Bell }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-surface-400 mt-1">Configure your dashboard and pipeline settings</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar */}
        <div className="lg:w-64 shrink-0">
          <Card>
            <CardContent className="p-2">
              <nav className="space-y-1">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                      activeTab === tab.id
                        ? 'bg-brand-500/20 text-brand-400'
                        : 'text-surface-400 hover:text-white hover:bg-surface-800'
                    )}
                  >
                    <tab.icon className="w-5 h-5" />
                    {tab.label}
                  </button>
                ))}
              </nav>
            </CardContent>
          </Card>
        </div>

        {/* Content */}
        <div className="flex-1 space-y-6">
          {activeTab === 'general' && (
            <>
              {/* System Status */}
              <Card>
                <CardHeader>
                  <CardTitle>System Status</CardTitle>
                  <CardDescription>Current health status of all services</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 rounded-lg bg-surface-800/50">
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            'w-10 h-10 rounded-lg flex items-center justify-center',
                            health?.status === 'healthy' ? 'bg-green-500/20' : 'bg-yellow-500/20'
                          )}
                        >
                          {health?.status === 'healthy' ? (
                            <CheckCircle className="w-5 h-5 text-green-500" />
                          ) : (
                            <AlertCircle className="w-5 h-5 text-yellow-500" />
                          )}
                        </div>
                        <div>
                          <p className="font-medium text-white">Overall Status</p>
                          <p className="text-sm text-surface-400">
                            {health?.status === 'healthy'
                              ? 'All systems operational'
                              : 'Some services degraded'}
                          </p>
                        </div>
                      </div>
                      <Badge variant={health?.status === 'healthy' ? 'success' : 'warning'} dot>
                        {health?.status || 'Unknown'}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="p-4 rounded-lg bg-surface-800/50">
                        <p className="text-sm text-surface-400">Version</p>
                        <p className="text-lg font-semibold text-white mt-1">
                          {health?.version || 'Unknown'}
                        </p>
                      </div>
                      <div className="p-4 rounded-lg bg-surface-800/50">
                        <p className="text-sm text-surface-400">Uptime</p>
                        <p className="text-lg font-semibold text-white mt-1">
                          {health?.uptime_seconds
                            ? formatDuration(health.uptime_seconds)
                            : 'Unknown'}
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Appearance */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Palette className="w-5 h-5" />
                    Appearance
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-surface-300 mb-2">
                        Theme
                      </label>
                      <Select
                        options={[
                          { value: 'dark', label: 'Dark' },
                          { value: 'light', label: 'Light' },
                          { value: 'system', label: 'System' }
                        ]}
                        defaultValue="dark"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-surface-300 mb-2">
                        Refresh Interval
                      </label>
                      <Select
                        options={[
                          { value: '5', label: '5 seconds' },
                          { value: '10', label: '10 seconds' },
                          { value: '30', label: '30 seconds' },
                          { value: '60', label: '1 minute' }
                        ]}
                        defaultValue="10"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}

          {activeTab === 'services' && (
            <Card>
              <CardHeader>
                <CardTitle>Service Health</CardTitle>
                <CardDescription>Status of connected services</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {health?.services?.map(
                    (service: {
                      name: string;
                      healthy: boolean;
                      message?: string;
                      latency_ms?: number;
                    }) => (
                      <div
                        key={service.name}
                        className="flex items-center justify-between p-4 rounded-lg bg-surface-800/50"
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className={cn(
                              'w-10 h-10 rounded-lg flex items-center justify-center',
                              service.healthy ? 'bg-green-500/20' : 'bg-red-500/20'
                            )}
                          >
                            {service.healthy ? (
                              <CheckCircle className="w-5 h-5 text-green-500" />
                            ) : (
                              <XCircle className="w-5 h-5 text-red-500" />
                            )}
                          </div>
                          <div>
                            <p className="font-medium text-white capitalize">
                              {service.name.replace(/_/g, ' ')}
                            </p>
                            <p className="text-sm text-surface-400">
                              {service.message || 'Connected'}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <Badge variant={service.healthy ? 'success' : 'danger'}>
                            {service.healthy ? 'Healthy' : 'Unhealthy'}
                          </Badge>
                          {service.latency_ms && (
                            <p className="text-xs text-surface-500 mt-1">
                              {service.latency_ms.toFixed(0)}ms
                            </p>
                          )}
                        </div>
                      </div>
                    )
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'storage' && (
            <Card>
              <CardHeader>
                <CardTitle>Storage Configuration</CardTitle>
                <CardDescription>Firestore and Cloud Storage settings</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Input label="Firestore Collection Prefix" defaultValue="creative_ads" disabled />
                  <Input
                    label="Raw Assets Bucket"
                    defaultValue="${PROJECT_ID}-raw-assets"
                    disabled
                  />
                  <Input
                    label="Processed Assets Bucket"
                    defaultValue="${PROJECT_ID}-processed-assets"
                    disabled
                  />
                  <p className="text-xs text-surface-500">
                    Storage configuration is managed via environment variables
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'gcp' && (
            <Card>
              <CardHeader>
                <CardTitle>GCP Configuration</CardTitle>
                <CardDescription>Google Cloud Platform settings</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Input label="Project ID" placeholder="your-gcp-project-id" disabled />
                  <Input label="Region" defaultValue="us-central1" disabled />
                  <Input label="Pub/Sub Topic" defaultValue="agentic-ads-jobs" disabled />
                  <div className="pt-4">
                    <a
                      href="https://console.cloud.google.com"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-brand-400 hover:text-brand-300 transition-colors"
                    >
                      Open GCP Console
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'notifications' && (
            <Card>
              <CardHeader>
                <CardTitle>Notification Settings</CardTitle>
                <CardDescription>Configure alerts and notifications</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-white">Failed Jobs</p>
                      <p className="text-sm text-surface-400">Get notified when jobs fail</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" defaultChecked className="sr-only peer" />
                      <div className="w-11 h-6 bg-surface-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-600"></div>
                    </label>
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-white">Error Rate Threshold</p>
                      <p className="text-sm text-surface-400">Alert when error rate exceeds 5%</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" defaultChecked className="sr-only peer" />
                      <div className="w-11 h-6 bg-surface-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-600"></div>
                    </label>
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-white">Queue Backlog</p>
                      <p className="text-sm text-surface-400">Alert when queue exceeds 100 items</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" className="sr-only peer" />
                      <div className="w-11 h-6 bg-surface-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-600"></div>
                    </label>
                  </div>
                  <div className="pt-4 border-t border-surface-800">
                    <Input label="Notification Email" type="email" placeholder="your@email.com" />
                  </div>
                  <Button>Save Notification Settings</Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
