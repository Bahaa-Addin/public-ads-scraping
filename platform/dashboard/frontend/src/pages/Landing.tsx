import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Sparkles,
  Layers,
  Zap,
  BarChart3,
  Image,
  MessageSquare,
  Activity,
  ChevronRight,
  LayoutDashboard,
  ListTodo,
  Radar,
  FileText,
  Settings,
  RefreshCw,
  Copy,
  Moon,
  Smartphone,
  Clock,
  Play,
  AlertCircle,
  CheckCircle
} from 'lucide-react';

// Stats shown in the hero
const stats = [
  { label: 'Assets Processed', value: '50K+' },
  { label: 'Industries Covered', value: '12' },
  { label: 'Avg. Processing Time', value: '<5s' },
  { label: 'Accuracy Rate', value: '95%' }
];

// Pipeline stages
const pipelineStages = [
  {
    step: 1,
    icon: Image,
    title: 'Scrape',
    description: 'Collect agentic ads from multiple platforms automatically',
    color: 'from-blue-500 to-cyan-500'
  },
  {
    step: 2,
    icon: Sparkles,
    title: 'Extract',
    description: 'AI analyzes visual elements, colors, layout, and CTAs',
    color: 'from-purple-500 to-pink-500'
  },
  {
    step: 3,
    icon: MessageSquare,
    title: 'Generate',
    description: 'Create detailed reverse-prompts for image generation',
    color: 'from-amber-500 to-orange-500'
  },
  {
    step: 4,
    icon: BarChart3,
    title: 'Analyze',
    description: 'Track metrics, trends, and industry distributions',
    color: 'from-emerald-500 to-teal-500'
  }
];

// Dashboard pages/sections
const dashboardPages = [
  {
    icon: LayoutDashboard,
    title: 'Dashboard',
    path: '/template/dashboard',
    description: 'Real-time pipeline metrics overview',
    features: [
      'Assets scraped counter',
      'Pipeline throughput chart',
      'Industry distribution pie',
      'Queue status & recent jobs'
    ],
    color: 'border-blue-500/30 hover:border-blue-500/60',
    iconBg: 'bg-blue-500/10 text-blue-400'
  },
  {
    icon: ListTodo,
    title: 'Jobs',
    path: '/template/jobs',
    description: 'Job queue management & monitoring',
    features: [
      'Bulk selection & actions',
      'Filter by status/type',
      'Retry failed jobs',
      'Real-time status updates'
    ],
    color: 'border-purple-500/30 hover:border-purple-500/60',
    iconBg: 'bg-purple-500/10 text-purple-400'
  },
  {
    icon: Image,
    title: 'Assets',
    path: '/template/assets',
    description: 'Browse scraped creative assets',
    features: [
      'Grid & list view modes',
      'Filter by industry/source',
      'Copy prompts to clipboard',
      'Reprocess assets'
    ],
    color: 'border-emerald-500/30 hover:border-emerald-500/60',
    iconBg: 'bg-emerald-500/10 text-emerald-400'
  },
  {
    icon: Radar,
    title: 'Scrapers',
    path: '/template/scrapers',
    description: 'Control & monitor web scrapers',
    features: [
      'Trigger scraping jobs',
      'Source selection',
      'Success rate tracking',
      'Rate limit monitoring'
    ],
    color: 'border-amber-500/30 hover:border-amber-500/60',
    iconBg: 'bg-amber-500/10 text-amber-400'
  },
  {
    icon: BarChart3,
    title: 'Analytics',
    path: '/template/analytics',
    description: 'Deep insights & visualization',
    features: [
      'Multi-metric time series',
      'Quality distribution',
      'CTA type breakdown',
      'Industry trends'
    ],
    color: 'border-cyan-500/30 hover:border-cyan-500/60',
    iconBg: 'bg-cyan-500/10 text-cyan-400'
  },
  {
    icon: FileText,
    title: 'Logs',
    path: '/template/logs',
    description: 'Application log viewer',
    features: [
      'Filter by level/service',
      'Full-text search',
      'Color-coded entries',
      'Real-time refresh'
    ],
    color: 'border-rose-500/30 hover:border-rose-500/60',
    iconBg: 'bg-rose-500/10 text-rose-400'
  }
];

// Key features
const keyFeatures = [
  {
    icon: RefreshCw,
    title: 'Real-Time Updates',
    description: 'Auto-refresh every 10-30 seconds',
    detail: 'React Query with automatic refetching'
  },
  {
    icon: Copy,
    title: 'Copy to Clipboard',
    description: 'One-click prompt copying',
    detail: 'Visual feedback with checkmark'
  },
  {
    icon: Moon,
    title: 'Dark Theme',
    description: 'Optimized for long sessions',
    detail: 'Reduced eye strain, better contrast'
  },
  {
    icon: Smartphone,
    title: 'Responsive Design',
    description: 'Mobile, tablet & desktop',
    detail: 'Hamburger menu on mobile'
  }
];

// Refresh intervals
const refreshIntervals = [
  { data: 'Dashboard metrics', interval: '10s' },
  { data: 'Jobs list', interval: '10s' },
  { data: 'Scraper status', interval: '10s' },
  { data: 'Health status', interval: '30s' }
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-surface-950 overflow-hidden">
      {/* Animated background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-radial from-brand-500/10 via-transparent to-transparent animate-pulse-slow" />
        <div
          className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-gradient-radial from-purple-500/10 via-transparent to-transparent animate-pulse-slow"
          style={{ animationDelay: '1.5s' }}
        />

        {/* Grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
            backgroundSize: '60px 60px'
          }}
        />
      </div>

      {/* Navigation */}
      <nav className="relative z-10 flex items-center justify-between px-6 lg:px-12 py-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-cyan-500 flex items-center justify-center shadow-glow">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <span className="text-xl font-bold text-white">Tasmem</span>
        </div>

        <Link
          to="/dashboard"
          className="group flex items-center gap-2 px-5 py-2.5 rounded-full bg-white/5 border border-white/10 text-white hover:bg-white/10 transition-all duration-300"
        >
          <span className="text-sm font-medium">Enter Dashboard</span>
          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </Link>
      </nav>

      {/* Hero / Jumbotron */}
      <section className="relative z-10 flex flex-col items-center justify-center px-6 pt-12 pb-16 lg:pt-16 lg:pb-20">
        {/* Badge */}
        <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-brand-500/10 border border-brand-500/20 mb-8 animate-fade-in">
          <Zap className="w-4 h-4 text-brand-400" />
          <span className="text-sm font-medium text-brand-400">
            AI-Powered Creative Intelligence
          </span>
        </div>

        {/* Main heading */}
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-center max-w-4xl leading-tight animate-slide-up">
          <span className="text-white">Transform Ads into</span>
          <br />
          <span className="bg-gradient-to-r from-brand-400 via-cyan-400 to-purple-400 bg-clip-text text-transparent">
            Generative Prompts
          </span>
        </h1>

        {/* Subtitle */}
        <p
          className="mt-6 text-lg text-surface-400 text-center max-w-2xl animate-slide-up"
          style={{ animationDelay: '0.1s' }}
        >
          Scrape, analyze, and reverse-engineer creative advertisements into detailed prompts for AI
          image generation.
        </p>

        {/* CTA buttons */}
        <div
          className="flex flex-col sm:flex-row items-center gap-4 mt-8 animate-slide-up"
          style={{ animationDelay: '0.2s' }}
        >
          <Link
            to="/template/dashboard"
            className="group flex items-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-brand-600 to-cyan-600 text-white font-semibold hover:from-brand-500 hover:to-cyan-500 transition-all duration-300 shadow-glow hover:shadow-glow-lg"
          >
            <Layers className="w-5 h-5" />
            <span>Explore Template Dashboard</span>
            <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </Link>

          <a
            href="#pipeline"
            className="px-8 py-4 rounded-xl text-surface-300 font-medium hover:text-white transition-colors"
          >
            Learn How It Works
          </a>
        </div>

        {/* Stats */}
        <div
          className="grid grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-12 mt-16 animate-fade-in"
          style={{ animationDelay: '0.3s' }}
        >
          {stats.map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-3xl lg:text-4xl font-bold text-white">{stat.value}</div>
              <div className="text-sm text-surface-500 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Pipeline Section */}
      <section
        id="pipeline"
        className="relative z-10 px-6 lg:px-12 py-20 border-t border-surface-800/50"
      >
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">
              How the Pipeline Works
            </h2>
            <p className="text-surface-400 max-w-2xl mx-auto">
              From raw ad creatives to AI-ready prompts in four automated stages
            </p>
          </div>

          {/* Pipeline flow */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {pipelineStages.map((stage, index) => (
              <div key={stage.title} className="relative group">
                {/* Connector line */}
                {index < pipelineStages.length - 1 && (
                  <div className="hidden lg:block absolute top-10 left-full w-full h-0.5 bg-gradient-to-r from-surface-700 to-surface-800 z-0" />
                )}

                <div className="relative p-6 rounded-2xl bg-surface-900/50 border border-surface-800 hover:border-surface-700 transition-all duration-300 h-full">
                  {/* Step number */}
                  <div className="absolute -top-3 -left-3 w-8 h-8 rounded-full bg-surface-800 border border-surface-700 flex items-center justify-center text-sm font-bold text-surface-400">
                    {stage.step}
                  </div>

                  <div
                    className={`w-14 h-14 rounded-xl bg-gradient-to-br ${stage.color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}
                  >
                    <stage.icon className="w-7 h-7 text-white" />
                  </div>
                  <h3 className="text-xl font-semibold text-white mb-2">{stage.title}</h3>
                  <p className="text-sm text-surface-400">{stage.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Dashboard Pages Section */}
      <section id="pages" className="relative z-10 px-6 lg:px-12 py-20 bg-surface-900/30">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">Dashboard Pages</h2>
            <p className="text-surface-400 max-w-2xl mx-auto">
              Six specialized views for complete pipeline management and monitoring
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {dashboardPages.map((page) => (
              <Link
                key={page.title}
                to={page.path}
                className={`group p-6 rounded-2xl bg-surface-900/80 border-2 ${page.color} transition-all duration-300 hover:bg-surface-800/80`}
              >
                <div className="flex items-start gap-4">
                  <div
                    className={`w-12 h-12 rounded-xl ${page.iconBg} flex items-center justify-center flex-shrink-0`}
                  >
                    <page.icon className="w-6 h-6" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-lg font-semibold text-white">{page.title}</h3>
                      <ArrowRight className="w-4 h-4 text-surface-500 group-hover:text-white group-hover:translate-x-1 transition-all" />
                    </div>
                    <p className="text-sm text-surface-400 mb-3">{page.description}</p>

                    <ul className="space-y-1">
                      {page.features.map((feature, i) => (
                        <li key={i} className="flex items-center gap-2 text-xs text-surface-500">
                          <CheckCircle className="w-3 h-3 text-emerald-500" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Settings card */}
          <div className="mt-6">
            <Link
              to="/template/settings"
              className="group flex items-center justify-between p-6 rounded-2xl bg-surface-900/80 border-2 border-surface-700/30 hover:border-surface-600/60 transition-all duration-300"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-surface-700/50 text-surface-400 flex items-center justify-center">
                  <Settings className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Settings</h3>
                  <p className="text-sm text-surface-400">
                    System status, appearance, service health & notifications
                  </p>
                </div>
              </div>
              <ArrowRight className="w-5 h-5 text-surface-500 group-hover:text-white group-hover:translate-x-1 transition-all" />
            </Link>
          </div>
        </div>
      </section>

      {/* Key Features Section */}
      <section className="relative z-10 px-6 lg:px-12 py-20 border-t border-surface-800/50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">Key Features</h2>
            <p className="text-surface-400 max-w-2xl mx-auto">
              Built for productivity with modern UX patterns
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {keyFeatures.map((feature) => (
              <div
                key={feature.title}
                className="p-6 rounded-2xl bg-surface-900/50 border border-surface-800"
              >
                <div className="w-12 h-12 rounded-xl bg-brand-500/10 flex items-center justify-center mb-4">
                  <feature.icon className="w-6 h-6 text-brand-400" />
                </div>
                <h3 className="text-lg font-semibold text-white mb-1">{feature.title}</h3>
                <p className="text-sm text-surface-400 mb-2">{feature.description}</p>
                <p className="text-xs text-surface-500">{feature.detail}</p>
              </div>
            ))}
          </div>

          {/* Refresh intervals table */}
          <div className="mt-12 p-6 rounded-2xl bg-surface-900/50 border border-surface-800">
            <div className="flex items-center gap-3 mb-4">
              <Clock className="w-5 h-5 text-brand-400" />
              <h3 className="text-lg font-semibold text-white">Auto-Refresh Intervals</h3>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {refreshIntervals.map((item) => (
                <div
                  key={item.data}
                  className="flex items-center justify-between p-3 rounded-lg bg-surface-800/50"
                >
                  <span className="text-sm text-surface-300">{item.data}</span>
                  <span className="text-sm font-mono text-brand-400">{item.interval}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Dashboard Preview Section */}
      <section className="relative z-10 px-6 lg:px-12 py-20 bg-surface-900/30">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">Dashboard Preview</h2>
            <p className="text-surface-400 max-w-2xl mx-auto">
              Modern dark theme interface optimized for monitoring
            </p>
          </div>

          {/* ASCII-style preview */}
          <div className="p-1 rounded-2xl bg-gradient-to-br from-brand-500/20 via-purple-500/20 to-cyan-500/20">
            <div className="p-6 rounded-xl bg-surface-950 font-mono text-xs sm:text-sm overflow-x-auto">
              <pre className="text-surface-400">
                {`┌─────────────────────────────────────────────────────────────────┐
│ ┌─────────┐                                        🔔  [Avatar] │
│ │Creative │  Dashboard           [Mock Data]  ● Connected       │
│ │  Ads    │─────────────────────────────────────────────────────│
│ │Pipeline │                                                      │
│ ├─────────┤  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐│
│ │⚗️ Templ. │  │`}
                <span className="text-blue-400">Assets</span>
                {`   │ │`}
                <span className="text-purple-400">Features</span>
                {` │ │`}
                <span className="text-emerald-400">Prompts</span>
                {`  │ │`}
                <span className="text-rose-400">Errors</span>
                {`  ││
│ │  Mock   │  │ `}
                <span className="text-white">1,234</span>
                {`    │ │ `}
                <span className="text-white">1,100</span>
                {`    │ │ `}
                <span className="text-white">987</span>
                {`      │ │ `}
                <span className="text-white">0.5%</span>
                {`   ││
│ │  data   │  │ `}
                <span className="text-emerald-400">▲ 12.5%</span>
                {`  │ │ `}
                <span className="text-emerald-400">▲ 8.3%</span>
                {`   │ │ `}
                <span className="text-emerald-400">▲ 15.2%</span>
                {`  │ │ `}
                <span className="text-emerald-400">▼ 2.1%</span>
                {` ││
│ ├─────────┤  └──────────┘ └──────────┘ └──────────┘ └─────────┘│
│ │📊 Dash  │                                                      │
│ │📋 Jobs  │  ┌─────────────────────────┐ ┌────────────────────┐ │
│ │🖼️ Assets│  │  `}
                <span className="text-cyan-400">Pipeline Throughput</span>
                {`     │ │  `}
                <span className="text-amber-400">Industry Dist.</span>
                {`   │ │
│ │📡 Scrape│  │  `}
                <span className="text-blue-400">▓▓▓▓▓▓</span>
                {`                │ │    `}
                <span className="text-blue-400">●</span>
                {` Finance     │ │
│ │📈 Analyt│  │  `}
                <span className="text-blue-400">▓▓▓▓▓▓▓▓▓▓</span>
                {`            │ │    `}
                <span className="text-purple-400">●</span>
                {` E-commerce  │ │
│ │📝 Logs  │  │  `}
                <span className="text-blue-400">▓▓▓▓▓▓▓▓</span>
                {`              │ │    `}
                <span className="text-emerald-400">●</span>
                {` SaaS        │ │
│ │⚙️ Settin│  └─────────────────────────┘ └────────────────────┘ │
│ ├─────────┤                                                      │
│ │🏠 Home  │  ┌─────────────────────────┐ ┌────────────────────┐ │
│ ├─────────┤  │  `}
                <span className="text-surface-300">Queue Status</span>
                {`          │ │  `}
                <span className="text-surface-300">Recent Jobs</span>
                {`      │ │
│ │System   │  │  Pending:     `}
                <span className="text-amber-400">15</span>
                {`       │ │  scrape    `}
                <span className="text-emerald-400">●done</span>
                {` │ │
│ │Status:  │  │  In Progress: `}
                <span className="text-blue-400">3</span>
                {`        │ │  extract   `}
                <span className="text-blue-400">●run</span>
                {`  │ │
│ │`}
                <span className="text-emerald-400">✓ Online</span>
                {` │  │  Completed:   `}
                <span className="text-emerald-400">542</span>
                {`      │ │  generate  `}
                <span className="text-amber-400">●wait</span>
                {` │ │
│ └─────────┘  └─────────────────────────┘ └────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘`}
              </pre>
            </div>
          </div>

          <p className="text-center text-surface-500 text-sm mt-4">
            Template dashboard with simulated data for demonstration
          </p>
        </div>
      </section>

      {/* Template Mode Notice */}
      <section className="relative z-10 px-6 lg:px-12 py-16 border-t border-surface-800/50">
        <div className="max-w-4xl mx-auto">
          <div className="p-6 rounded-2xl bg-amber-500/5 border border-amber-500/20">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center flex-shrink-0">
                <AlertCircle className="w-6 h-6 text-amber-500" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-amber-500 mb-2">Template Mode</h3>
                <p className="text-surface-400 mb-4">
                  The dashboard runs with <strong className="text-surface-300">mock data</strong>{' '}
                  for demonstration purposes. In production, you would connect to real GCP services
                  (Firestore, Cloud Run, Pub/Sub) for live data.
                </p>
                <div className="flex flex-wrap gap-3">
                  <span className="px-3 py-1 rounded-full bg-surface-800 text-xs text-surface-400">
                    50 sample jobs
                  </span>
                  <span className="px-3 py-1 rounded-full bg-surface-800 text-xs text-surface-400">
                    100 sample assets
                  </span>
                  <span className="px-3 py-1 rounded-full bg-surface-800 text-xs text-surface-400">
                    500 sample logs
                  </span>
                  <span className="px-3 py-1 rounded-full bg-surface-800 text-xs text-surface-400">
                    Simulated metrics
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 px-6 lg:px-12 py-20">
        <div className="max-w-4xl mx-auto text-center">
          <div className="p-12 rounded-3xl bg-gradient-to-br from-surface-900 to-surface-900/50 border border-surface-800">
            <h2 className="text-2xl lg:text-3xl font-bold text-white mb-4">Ready to explore?</h2>
            <p className="text-surface-400 mb-8">
              Dive into the template dashboard and see all features in action
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                to="/template/dashboard"
                className="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-white text-surface-950 font-semibold hover:bg-surface-100 transition-all duration-300"
              >
                <Play className="w-5 h-5" />
                <span>Enter Template Dashboard</span>
              </Link>
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-8 py-4 rounded-xl text-surface-300 font-medium hover:text-white transition-colors"
              >
                View Documentation
                <ArrowRight className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 px-6 lg:px-12 py-8 border-t border-surface-800/50">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-surface-500">
              <Activity className="w-4 h-4" />
              <span className="text-sm">Tasmem Agentic Ads Platform</span>
            </div>

            <div className="flex items-center gap-6 text-sm text-surface-500">
              <span>Version 2.0.0</span>
              <span>•</span>
              <span>React + TypeScript + Tailwind</span>
              <span>•</span>
              <span className="text-amber-500">Demo Mode</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
