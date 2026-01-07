# Creative Ads Dashboard - User Guide

> **Version**: 2.0.0  
> **Tech Stack**: React 18 + TypeScript + Tailwind CSS + Vite  
> **URL**: http://localhost:5173

---

## 📖 Table of Contents

1. [Getting Started](#getting-started)
2. [Application Structure](#application-structure)
3. [Landing Page](#landing-page)
4. [Template Dashboard](#template-dashboard)
   - [Navigation](#navigation)
   - [Dashboard (Home)](#dashboard-home)
   - [Jobs](#jobs)
   - [Assets](#assets)
   - [Scrapers](#scrapers)
   - [Analytics](#analytics)
   - [Logs](#logs)
   - [Settings](#settings)
5. [Features Deep Dive](#features-deep-dive)
6. [Keyboard Shortcuts](#keyboard-shortcuts)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

- Node.js 18+
- Agent API running on port 8081
- Dashboard Backend running on port 8000

### Starting the Dashboard

```bash
cd dashboard/frontend
npm install  # First time only
npm run dev
```

Then open **http://localhost:5173** in your browser.

---

## Application Structure

The application is organized into three main sections:

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   /                    → Landing Page (Jumbotron)                    │
│                          Entry point with feature showcase           │
│                                                                      │
│   /dashboard/*         → Live Dashboard                              │
│                          Real data mode with empty state handling    │
│                                                                      │
│   /template/*          → Template Dashboard                          │
│                          Demo mode with mock/sample data             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Route Map

| Route | Mode | Description |
|-------|------|-------------|
| `/` | - | Landing page with feature showcase |
| `/dashboard` | **Live** | Pipeline metrics (real data) |
| `/jobs` | **Live** | Job queue management (real data) |
| `/assets` | **Live** | Browse creatives (real data) |
| `/scrapers` | **Live** | Control scrapers (real actions) |
| `/analytics` | **Live** | Insights & charts (real data) |
| `/logs` | **Live** | Application logs (real data) |
| `/settings` | **Live** | Configuration (real settings) |
| `/template/dashboard` | Demo | Pipeline metrics (mock data) |
| `/template/jobs` | Demo | Job queue (mock data) |
| `/template/assets` | Demo | Browse creatives (mock data) |
| `/template/scrapers` | Demo | Scrapers (mock data) |
| `/template/analytics` | Demo | Analytics (mock data) |
| `/template/logs` | Demo | Logs (mock data) |
| `/template/settings` | Demo | Settings (mock data) |

### Dashboard Modes

| Mode | Badge Color | Data Source | Actions |
|------|-------------|-------------|---------|
| **Live** | 🟢 Green | Real backend/Firestore | Real scraping, real jobs |
| **Template** | 🟠 Amber | Mock data | Safe to explore, no side effects |

---

## Landing Page

**URL**: `/`

The entry point of the application—a modern jumbotron-style landing page.

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Logo] Tasmem                              [View Dashboard →]        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│             ⚡ AI-Powered Creative Intelligence                      │
│                                                                      │
│                   Transform Ads into                                 │
│                 Generative Prompts                                   │
│                                                                      │
│     Scrape, analyze, and reverse-engineer creative advertisements   │
│         into detailed prompts for AI image generation.              │
│                                                                      │
│         [🔲 Explore Template Dashboard →]    Learn More              │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│     50K+          │      12       │     <5s      │      95%          │
│  Assets Processed │   Industries  │  Avg. Time   │  Accuracy         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│                  FULL PIPELINE CAPABILITIES                          │
│                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│
│  │ 🖼️ Asset     │ │ ✨ Feature   │ │ 💬 Prompt    │ │ 📊 Analytics ││
│  │   Scraping   │ │  Extraction  │ │  Generation  │ │              ││
│  │              │ │              │ │              │ │              ││
│  │ Automated    │ │ AI-powered   │ │ Reverse-     │ │ Track        ││
│  │ collection   │ │ analysis of  │ │ engineer ads │ │ performance  ││
│  │ from multiple│ │ visual       │ │ into detailed│ │ metrics and  ││
│  │ platforms    │ │ elements     │ │ prompts      │ │ trends       ││
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘│
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│              Ready to explore the template?                          │
│                                                                      │
│           [Enter Template Dashboard →]                               │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│ [Logo] Tasmem Creative Ads Platform      Demo Dashboard with Mock Data│
└─────────────────────────────────────────────────────────────────────┘
```

### Landing Page Sections

| Section | Description |
|---------|-------------|
| **Navigation** | Logo and "View Dashboard" button |
| **Hero** | Main headline with gradient text and CTA buttons |
| **Stats** | Key metrics (Assets, Industries, Time, Accuracy) |
| **Features** | Four capability cards with icons |
| **CTA Section** | Final call-to-action to enter dashboard |
| **Footer** | Branding and mock data notice |

### Visual Effects

- Animated gradient background with radial glows
- Grid pattern overlay
- Staggered fade-in animations
- Hover effects on cards and buttons
- Shadow glow on primary CTA button

---

## Template Dashboard

**Base URL**: `/template`

The template dashboard is a fully-functional demo environment with **mock data**. All routes under `/template/*` use sample data to demonstrate the platform's capabilities.

> ⚠️ **Note**: Data in the template dashboard is simulated. In production, you would connect to real data sources.

### Template Mode Indicators

The dashboard clearly indicates it's running in template mode:

1. **Sidebar Badge**: Amber "Template Mode - Using mock data" badge
2. **Header Tag**: "Mock Data" badge next to page title
3. **Back to Home**: Link in sidebar to return to landing page

---

## Navigation

### Sidebar Menu

| Icon | Page | URL | Description |
|------|------|-----|-------------|
| 📊 | Dashboard | `/template/dashboard` | Overview metrics and charts |
| 📋 | Jobs | `/template/jobs` | Job queue management |
| 🖼️ | Assets | `/template/assets` | Browse scraped creatives |
| 📡 | Scrapers | `/template/scrapers` | Control scraping sources |
| 📈 | Analytics | `/template/analytics` | Deep insights and charts |
| 📝 | Logs | `/template/logs` | Application logs viewer |
| ⚙️ | Settings | `/template/settings` | Configuration options |
| 🏠 | Home | `/` | Back to landing page |

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ ┌─────────┐                                          🔔  [Avatar]  │
│ │Creative │  Dashboard              [Mock Data]  ● Connected       │
│ │  Ads    │──────────────────────────────────────────────────────── │
│ │Pipeline │                                                         │
│ │Dashboard│                                                         │
│ ├─────────┤  ┌─────────────────────────────────────────────────┐   │
│ │[⚗️ Temp.]│  │                                                  │   │
│ │ Mock    │  │              MAIN CONTENT AREA                   │   │
│ │  data   │  │                                                  │   │
│ ├─────────┤  │         Charts, Tables, Forms, etc.              │   │
│ │📊 Dash  │  │                                                  │   │
│ │📋 Jobs  │  │                                                  │   │
│ │🖼️ Assets│  │                                                  │   │
│ │📡 Scrape│  │                                                  │   │
│ │📈 Analyt│  └─────────────────────────────────────────────────┘   │
│ │📝 Logs  │                                                         │
│ │⚙️ Settin│                                                         │
│ ├─────────┤                                                         │
│ │🏠 Home  │                                                         │
│ ├─────────┤                                                         │
│ │System   │                                                         │
│ │Status:  │                                                         │
│ │✓ Online │                                                         │
│ └─────────┘                                                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Mobile Navigation

On mobile devices, the sidebar becomes a hamburger menu (☰) in the top-left corner.

---

## Dashboard (Home)

**URL**: `/template/dashboard`

The main overview page showing real-time pipeline metrics.

```
┌──────────────────────────────────────────────────────────────────┐
│                         DASHBOARD                                │
├──────────────┬───────────────┬───────────────┬──────────────────┤
│ Assets       │ Features      │ Prompts       │ Error Rate       │
│ Scraped      │ Extracted     │ Generated     │                  │
│   1,234      │   1,100       │   987         │   0.5%           │
│  ▲ 12.5%     │  ▲ 8.3%       │  ▲ 15.2%      │  ▼ 2.1%          │
├──────────────┴───────────────┴───────────────┴──────────────────┤
│                                                                  │
│  Pipeline Throughput (24h)           │ Industry Distribution    │
│  ┌────────────────────────────┐     │  ┌──────────────────┐    │
│  │ ▓▓▓▓▓                      │     │  │    [Pie Chart]   │    │
│  │ ▓▓▓▓▓▓▓▓▓                  │     │  │                  │    │
│  │ ▓▓▓▓▓▓▓                    │     │  │  ● Finance       │    │
│  │ ▓▓▓▓▓▓▓▓▓▓▓▓               │     │  │  ● E-commerce    │    │
│  └────────────────────────────┘     │  │  ● SaaS          │    │
│                                      │  └──────────────────┘    │
├──────────────────────────────────────┴──────────────────────────┤
│  Queue Status              │  Recent Jobs                       │
│  ├ Pending:     15         │  ├ scrape         ● completed      │
│  ├ In Progress: 3          │  ├ extract        ● in_progress    │
│  ├ Completed:   542        │  ├ generate       ● pending        │
│  └ Failed:      2          │  └ scrape         ● failed         │
└──────────────────────────────────────────────────────────────────┘
```

### Key Metrics

| Metric | Description | Update Interval |
|--------|-------------|-----------------|
| **Assets Scraped** | Total creative ads collected | 10s |
| **Features Extracted** | Assets processed by feature extraction | 10s |
| **Prompts Generated** | Reverse-prompts created | 10s |
| **Error Rate** | Percentage of failed operations | 10s |

### Charts

1. **Pipeline Throughput**: Area chart showing assets processed over 24 hours
2. **Industry Distribution**: Pie chart of asset categories
3. **Queue Status**: Current job queue breakdown
4. **Recent Jobs**: Latest 5 jobs with status

---

## Jobs

**URL**: `/template/jobs`

Manage and monitor pipeline jobs.

```
┌──────────────────────────────────────────────────────────────────┐
│ JOB QUEUE                                    [Retry Failed (5)]  │
├──────────┬───────────┬───────────┬──────────┬──────────┬────────┤
│ Pending  │ In Prog   │ Completed │ Failed   │ Retrying │ Cancel │
│    15    │     3     │    542    │    5     │    2     │   0    │
├──────────┴───────────┴───────────┴──────────┴──────────┴────────┤
│                                                                  │
│  [All Statuses ▼] [All Types ▼] [Search...]                     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ ☐ │ Job ID   │ Type           │ Source │ Status │ Created  │ │
│  ├───┼──────────┼────────────────┼────────┼────────┼──────────┤ │
│  │ ☑ │ abc123.. │ scrape         │ Meta   │ ●done  │ 5m ago   │ │
│  │ ☐ │ def456.. │ extract_feat.. │ -      │ ●run   │ 2m ago   │ │
│  │ ☐ │ ghi789.. │ generate_pro.. │ -      │ ●wait  │ 1m ago   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  [< Page 1 >]    Showing 1-15 of 560                            │
└──────────────────────────────────────────────────────────────────┘
```

### Features

| Feature | Description |
|---------|-------------|
| **Bulk Selection** | Select multiple jobs with checkboxes |
| **Retry Failed** | One-click retry all failed jobs |
| **Filter by Status** | pending, in_progress, completed, failed, retrying, cancelled |
| **Filter by Type** | scrape, extract_features, generate_prompt, classify_industry |
| **Pagination** | Navigate through large job lists |

### Job Actions

- **Retry**: Re-queue selected failed jobs
- **Cancel**: Stop selected pending/in-progress jobs

---

## Assets

**URL**: `/template/assets`

Browse and manage scraped creative assets.

```
┌──────────────────────────────────────────────────────────────────┐
│ CREATIVE ASSETS                    [Export] [Grid|List]          │
├──────────────────────────────────────────────────────────────────┤
│ [All Industries▼] [All Sources▼] [CTA Type▼] [Prompts▼] [Search] │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐             │
│  │ [Image] │  │ [Image] │  │ [Image] │  │ [Image] │             │
│  │ ☐ Tech  │  │ ☐ Fin   │  │ ☐ SaaS  │  │ ☐ E-com │             │
│  ├─────────┤  ├─────────┤  ├─────────┤  ├─────────┤             │
│  │ Title   │  │ Title   │  │ Title   │  │ Title   │             │
│  │ Meta •5m│  │ Google• │  │ Archive │  │ Meta •  │             │
│  │ [hero]  │  │ [split] │  │ [mini]  │  │ [hero]  │             │
│  │─────────│  │─────────│  │─────────│  │─────────│             │
│  │ "A mode │  │ "Clean  │  │ "Dark   │  │ "Vibran │             │
│  │ rn..." 📋│  │ ..." 📋 │  │ ..." 📋 │  │ t..." 📋│             │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘             │
│                                                                  │
│  [< Page 1 >]    Showing 1-12 of 1,234                          │
└──────────────────────────────────────────────────────────────────┘
```

### View Modes

| Mode | Description |
|------|-------------|
| **Grid** | Card layout with thumbnails (default) |
| **List** | Compact row layout |

### Filters

| Filter | Options |
|--------|---------|
| **Industry** | Finance, E-commerce, SaaS, Healthcare, etc. |
| **Source** | Meta Ad Library, Google Ads, Internet Archive, etc. |
| **CTA Type** | Shop Now, Learn More, Sign Up, etc. |
| **Has Prompt** | With Prompt / Without Prompt |
| **Search** | Full-text search across titles and descriptions |

### Asset Card Features

- **Thumbnail**: Preview image
- **Industry Badge**: Top-right corner classification
- **Title**: Asset title or advertiser name
- **Source & Time**: Where it came from and when
- **Feature Tags**: Layout type, CTA type
- **Prompt Preview**: Generated reverse-prompt (truncated)
- **Copy Button** (📋): Copy full prompt to clipboard

### Bulk Actions

- **Reprocess**: Re-run feature extraction and prompt generation
- **Export**: Download selected assets as JSON/CSV

---

## Scrapers

**URL**: `/template/scrapers`

Control and monitor web scrapers.

```
┌──────────────────────────────────────────────────────────────────┐
│ SCRAPERS                                         [Trigger All]   │
├───────────────┬───────────────┬───────────────┬─────────────────┤
│ 🟢 Running: 2 │ 📊 Total: 15k │ ✓ Success: 98%│ 📡 Sources: 4   │
├───────────────┴───────────────┴───────────────┴─────────────────┤
│                                                                  │
│  TRIGGER SCRAPING JOBS                                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Select Sources:                                             │ │
│  │ [Meta Ad Library] [Google Ads] [Internet Archive] [Wiki]   │ │
│  │                                                             │ │
│  │ Search Query (optional): [fintech, SaaS____________]       │ │
│  │ Max Items per Source:    [100 items ▼]                     │ │
│  │                                                             │ │
│  │                           [▶ Start Scraping (2 sources)]   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────┐  ┌─────────────────────────┐      │
│  │ 📡 Meta Ad Library      │  │ 📡 Google Ads           │      │
│  │    ● Running            │  │    ○ Idle               │      │
│  │ ├ Items: 8,234          │  │ ├ Items: 4,521          │      │
│  │ ├ Success: 99.2%        │  │ ├ Success: 97.8%        │      │
│  │ └ Last run: 5m ago      │  │ └ Last run: 2h ago      │      │
│  └─────────────────────────┘  └─────────────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
```

### Trigger Panel

| Field | Description |
|-------|-------------|
| **Select Sources** | Click to toggle sources (multi-select) |
| **Search Query** | Optional filter for scraped content |
| **Max Items** | 25, 50, 100, 200, or 500 per source |

### Scraper Cards

Each scraper shows:
- **Status**: Running (🟢 animated), Idle (🔵), Disabled (⚫)
- **Items Scraped**: Total collected count
- **Success Rate**: Color-coded (>95% green, >80% yellow, else red)
- **Last Run**: Relative timestamp
- **Errors**: Error count and last error message

### Quick Actions

| Button | Action |
|--------|--------|
| **Trigger All** | Start scraping on all enabled sources |
| **Start Scraping** | Start selected sources with configured options |

---

## Analytics

**URL**: `/template/analytics`

Deep insights and visualization.

```
┌──────────────────────────────────────────────────────────────────┐
│ ANALYTICS                                    [Last 24 hours ▼]   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PIPELINE THROUGHPUT OVER TIME                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │      ───── Assets Scraped                                   │ │
│  │      ───── Features Extracted                               │ │
│  │      ───── Prompts Generated                                │ │
│  │  100│     ╱╲                                                │ │
│  │   80│   ╱    ╲    ╱╲                                        │ │
│  │   60│ ╱        ╲╱    ╲                                      │ │
│  │   40│                  ╲╱                                   │ │
│  │     └────────────────────────────────────────────────────   │ │
│  │       00:00   04:00   08:00   12:00   16:00   20:00         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
├─────────────────────────────────┬────────────────────────────────┤
│ INDUSTRY DISTRIBUTION           │ ASSETS BY SOURCE               │
│  ┌────────────────────┐        │  Meta Ad Library    ████████ 8k│
│  │     [Pie Chart]    │        │  Google Ads         █████   5k │
│  │                    │        │  Internet Archive   ███     3k │
│  │  Finance     35%   │        │  Wikimedia          █       1k │
│  │  E-commerce  28%   │        │                                │
│  │  SaaS        20%   │        │                                │
│  └────────────────────┘        │                                │
├─────────────────────────────────┼────────────────────────────────┤
│ QUALITY SCORE DISTRIBUTION      │ CTA TYPE DISTRIBUTION          │
│  [Bar Chart]                    │  [Bar Chart]                   │
│  0.0-0.2  ██                    │  Shop Now    █████████         │
│  0.2-0.4  █████                 │  Learn More  ███████           │
│  0.4-0.6  ████████              │  Sign Up     █████             │
│  0.6-0.8  ███████████████       │  Get Started ████              │
│  0.8-1.0  ████████████          │  Download    ███               │
└─────────────────────────────────┴────────────────────────────────┘
```

### Time Range Selector

| Option | Description |
|--------|-------------|
| Last 6 hours | Short-term monitoring |
| Last 24 hours | Daily overview (default) |
| Last 3 days | Short-term trends |
| Last 7 days | Weekly analysis |

### Charts

1. **Pipeline Throughput**: Multi-line chart showing all metrics over time
2. **Industry Distribution**: Donut chart with percentage breakdown
3. **Assets by Source**: Horizontal bar chart
4. **Quality Score**: Distribution histogram
5. **CTA Types**: Most common call-to-action types

### Industry Breakdown Table

Detailed table showing:
- Industry name with color indicator
- Count
- Percentage
- Visual progress bar

---

## Logs

**URL**: `/template/logs`

Application log viewer.

```
┌──────────────────────────────────────────────────────────────────┐
│ LOGS                                                             │
├──────────────────────────────────────────────────────────────────┤
│ [All Levels ▼] [All Services ▼] [Search logs...]    [⟳ Refresh] │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  2024-01-15 14:32:15  INFO   agent     Pipeline started          │
│  2024-01-15 14:32:16  INFO   scraper   Fetching from Meta...     │
│  2024-01-15 14:32:18  WARN   storage   Rate limit approaching    │
│  2024-01-15 14:32:20  ERROR  llm       Generation failed: ...    │
│  2024-01-15 14:32:22  INFO   agent     Retry scheduled           │
│  2024-01-15 14:32:25  DEBUG  queue     Job abc123 completed      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Filters

| Filter | Options |
|--------|---------|
| **Level** | DEBUG, INFO, WARNING, ERROR |
| **Service** | agent, scraper, storage, llm, queue |
| **Search** | Full-text search in log messages |

### Log Entry Colors

| Level | Color |
|-------|-------|
| DEBUG | Gray |
| INFO | Blue |
| WARNING | Yellow |
| ERROR | Red |

---

## Settings

**URL**: `/template/settings`

Configuration and system status.

```
┌──────────────────────────────────────────────────────────────────┐
│ SETTINGS                                                         │
├─────────────┬────────────────────────────────────────────────────┤
│             │                                                    │
│ ○ General   │  SYSTEM STATUS                                     │
│ ○ Services  │  ┌───────────────────────────────────────────────┐│
│ ○ Storage   │  │ ✓ All Systems Operational       [Healthy]     ││
│ ○ GCP       │  │                                               ││
│ ○ Notific.. │  │ Version: 1.0.0    │    Uptime: 2d 5h 30m     ││
│             │  └───────────────────────────────────────────────┘│
│             │                                                    │
│             │  APPEARANCE                                        │
│             │  Theme:            [Dark ▼]                        │
│             │  Refresh Interval: [10 seconds ▼]                  │
│             │                                                    │
└─────────────┴────────────────────────────────────────────────────┘
```

### Settings Tabs

| Tab | Contents |
|-----|----------|
| **General** | System status, appearance, refresh interval |
| **Services** | Health status of all connected services |
| **Storage** | Firestore and Cloud Storage configuration (read-only) |
| **GCP** | Google Cloud Platform settings (read-only) |
| **Notifications** | Alert configuration (Failed Jobs, Error Rate, Queue Backlog) |

### System Status

- **Overall Status**: Healthy / Partial Degradation
- **Version**: Current application version
- **Uptime**: Time since last restart
- **Service Health**: Individual service status with latency

---

## Features Deep Dive

### Real-Time Updates

The dashboard uses React Query with automatic refetching:

| Data | Refresh Interval |
|------|-----------------|
| Dashboard metrics | 10 seconds |
| Jobs list | 10 seconds |
| Recent jobs | 15 seconds |
| Job stats | 15 seconds |
| Scraper status | 10 seconds |
| Health status | 30 seconds |

### Copy to Clipboard

On asset cards, click the 📋 icon to copy the generated reverse-prompt:
- Shows ✓ checkmark on success
- Automatically clears after 2 seconds

### Responsive Design

| Breakpoint | Behavior |
|------------|----------|
| Mobile (<640px) | Hamburger menu, single column |
| Tablet (640-1024px) | 2-column grid, compact sidebar |
| Desktop (>1024px) | Full sidebar, multi-column layouts |

### Dark Theme

The dashboard uses a dark theme optimized for:
- Reduced eye strain during long monitoring sessions
- Better contrast for charts and data visualization
- Modern, professional appearance

### Mode Indicators

Both dashboard modes clearly indicate their data source:

**Live Mode (Green):**
| Location | Indicator |
|----------|-----------|
| Sidebar | Green "⚡ Live Mode - Connected to real data" badge |
| Header | "Live" tag next to page title |

**Template Mode (Amber):**
| Location | Indicator |
|----------|-----------|
| Sidebar | Amber "⚗️ Template Mode - Using mock data" badge |
| Header | "Mock Data" tag next to page title |
| Landing Page | "Demo Dashboard with Mock Data" in footer |

### Empty State Handling

When running in **Live Mode** with no data, pages display helpful empty states:

| Page | Empty State Message | Action |
|------|---------------------|--------|
| Dashboard | "No throughput data yet" / "No industry data yet" | - |
| Jobs | "No jobs yet" | Start scraping |
| Assets | "No assets yet" | Go to Scrapers |
| Logs | "No logs yet" | Wait for pipeline activity |
| Analytics | Charts show "No data" placeholders | - |

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Esc` | Close mobile sidebar |
| `Enter` | Submit search/filter |

---

## Troubleshooting

### Dashboard Won't Load

1. Check if frontend is running:
   ```bash
   cd dashboard/frontend && npm run dev
   ```

2. Check browser console for errors (F12 → Console)

3. Verify backend is accessible:
   ```bash
   curl http://localhost:8000/health
   ```

### "Connection Lost" Status

The dashboard shows "Degraded" when it can't reach the backend:

1. Ensure Dashboard Backend is running on port 8000
2. Ensure Agent API is running on port 8081
3. Check CORS configuration

### Data Not Updating

1. Check network tab for failed API calls
2. Hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
3. Clear browser cache

### Charts Not Displaying

1. Ensure you have data in the system
2. Check browser console for JavaScript errors
3. Try a different time range

### Landing Page Not Showing

If you're redirected directly to the dashboard:
1. Clear browser cache
2. Navigate explicitly to `http://localhost:5173/`
3. Check that `App.tsx` has the correct routing

---

## API Endpoints Used

The frontend communicates with these backend endpoints:

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | System health check |
| `GET /api/v1/metrics/dashboard` | Dashboard metrics |
| `GET /api/v1/jobs` | List jobs |
| `POST /api/v1/jobs/control` | Control jobs (retry/cancel) |
| `GET /api/v1/assets` | List assets |
| `GET /api/v1/scrapers/status` | Scraper status |
| `POST /api/v1/scrapers/trigger` | Trigger scraping |
| `GET /api/v1/logs` | Fetch logs |

---

## Quick Start Checklist

### For Live Dashboard (Real Data)
- [ ] Start Agent API: `MODE=local ./venv/bin/uvicorn agent.api:app --port 8081`
- [ ] Start Dashboard Backend: `cd dashboard/backend && uvicorn app.main:app --port 8000`
- [ ] Start Dashboard Frontend: `cd dashboard/frontend && npm run dev`
- [ ] Open http://localhost:5173 (Landing Page)
- [ ] Click "Enter Dashboard" (top-right) to go to `/dashboard`
- [ ] Verify green "Live" badge and "Connected" status
- [ ] Trigger scraping to populate data
- [ ] Navigate through all pages to verify functionality

### For Template Dashboard (Demo Mode)
- [ ] Start Dashboard Frontend: `cd dashboard/frontend && npm run dev`
- [ ] Open http://localhost:5173 (Landing Page)
- [ ] Click "Explore Template Dashboard" to enter `/template/dashboard`
- [ ] Verify amber "Mock Data" badge in header
- [ ] Browse all pages with pre-populated sample data
- [ ] Use "Back to Home" in sidebar to return to landing page

---

## File Structure

```
dashboard/frontend/
├── src/
│   ├── App.tsx                 # Main routing (/, /dashboard/*, /template/*)
│   ├── components/
│   │   ├── Layout.tsx          # Live dashboard layout (green "Live" badge)
│   │   ├── TemplateLayout.tsx  # Template dashboard layout (amber "Mock" badge)
│   │   └── ui/
│   │       ├── EmptyState.tsx  # Empty state component for no-data scenarios
│   │       ├── Badge.tsx
│   │       ├── Button.tsx
│   │       ├── Card.tsx
│   │       ├── Input.tsx
│   │       ├── Select.tsx
│   │       ├── StatCard.tsx
│   │       └── Table.tsx
│   ├── pages/
│   │   ├── Landing.tsx         # Landing page with feature showcase (/)
│   │   ├── Dashboard.tsx       # Dashboard (shared by both modes)
│   │   ├── Jobs.tsx            # Jobs (shared, with empty state)
│   │   ├── Assets.tsx          # Assets (shared, with empty state)
│   │   ├── Scrapers.tsx        # Scrapers (shared, with empty state)
│   │   ├── Analytics.tsx       # Analytics (shared)
│   │   ├── Logs.tsx            # Logs (shared, with empty state)
│   │   └── Settings.tsx        # Settings (shared)
│   ├── lib/
│   │   ├── api.ts              # API client functions
│   │   └── utils.ts            # Utility functions
│   ├── index.css               # Global styles
│   └── main.tsx                # Entry point
├── DASHBOARD_GUIDE.md          # This file
└── package.json
```

---

## Support

For issues or questions:
1. Check the [MANUAL_TESTING.md](../../MANUAL_TESTING.md) guide
2. Review browser console for errors
3. Check backend logs for API issues

