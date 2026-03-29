# 🎨 Agentic Ads Dashboard

A comprehensive full-stack monitoring and control dashboard for the Agentic Agentic Ads Pipeline. This dashboard provides real-time visibility and control over scraping jobs, feature extraction, reverse-prompt generation, and industry classification.

![Dashboard Architecture](./docs/architecture.png)

## ✨ Features

### 📊 Job Control Panel

- View all active jobs with status, timestamps, and asset counts
- Start, stop, pause, resume, and retry jobs
- Queue new scraping tasks by platform/source
- Real-time job status updates via WebSocket

### 🔍 Scraper Monitoring

- Real-time logs with color-coded severity levels
- Success/failure rates per source
- Error categorization and tracking
- Performance metrics and throughput

### 🎯 Feature Extraction & Reverse-Prompting

- Grid/table view of all processed assets
- Extracted features display (colors, layout, typography, CTAs)
- Reverse and negative prompts
- Search and filter by industry, source, features
- Re-run extraction or prompt generation for specific assets

### 📈 Industry Classification Dashboard

- Pie/bar charts for industry distribution
- Sub-category breakdowns
- Prompt quality heatmaps
- Manual classification override

### 📉 Metrics & System Monitoring

- Scraper throughput (assets/minute)
- Feature extraction latency
- Reverse-prompt generation time
- Cloud Run/Cloud Function utilization
- Pub/Sub queue length and backlog
- Custom metric dashboards

### 📋 Logs & Notifications

- Searchable, filterable log viewer
- Color-coded by severity
- Real-time log streaming
- Email/Slack notification integration

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Dashboard Frontend                         │
│                    (React + Tailwind CSS)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │   Jobs   │ │  Assets  │ │Analytics │ │   Logs   │            │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘            │
└───────┼────────────┼────────────┼────────────┼──────────────────┘
        │            │            │            │
        └────────────┴─────┬──────┴────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                   Dashboard API (FastAPI)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ /jobs/*  │ │/assets/* │ │/metrics/*│ │ /logs/*  │            │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘            │
└───────┼────────────┼────────────┼────────────┼──────────────────┘
        │            │            │            │
┌───────┴────────────┴────────────┴────────────┴──────────────────┐
│                     Backend Services                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  Agent Brain │  │   Scrapers   │  │   Feature    │           │
│  │   (Python)   │  │   (Node.js)  │  │  Extraction  │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
┌─────────┴─────────────────┴─────────────────┴───────────────────┐
│                        GCP Services                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │Firestore │ │  Storage │ │ Pub/Sub  │ │Vertex AI │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker & Docker Compose
- GCP Account with enabled APIs
- Terraform 1.5+ (for infrastructure)

### Local Development

1. **Clone the repository**

   ```bash
   cd platform/dashboard
   ```

2. **Set up environment variables**

   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Start with Docker Compose**

   ```bash
   # Start all services including emulators
   docker-compose up -d

   # Or start with hot-reload for development
   docker-compose --profile dev up -d
   ```

4. **Access the dashboard**
   - Frontend: http://localhost:80 (or http://localhost:5173 for dev mode)
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Manual Setup (Without Docker)

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## 📁 Project Structure

```
dashboard/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── main.py         # FastAPI application entry
│   │   ├── config.py       # Configuration management
│   │   ├── models.py       # Pydantic models
│   │   ├── routers/        # API route handlers
│   │   │   ├── jobs.py
│   │   │   ├── assets.py
│   │   │   ├── metrics.py
│   │   │   ├── scrapers.py
│   │   │   ├── logs.py
│   │   │   └── health.py
│   │   └── services/       # Business logic services
│   │       ├── firestore_service.py
│   │       ├── job_service.py
│   │       └── metrics_service.py
│   ├── tests/              # Backend tests
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/               # React Frontend
│   ├── src/
│   │   ├── main.tsx       # React entry point
│   │   ├── App.tsx        # Root component with routing
│   │   ├── components/    # Reusable UI components
│   │   │   ├── Layout.tsx
│   │   │   ├── ui/        # Base UI components
│   │   │   └── charts/    # Chart components
│   │   ├── pages/         # Page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Jobs.tsx
│   │   │   ├── Assets.tsx
│   │   │   ├── Scrapers.tsx
│   │   │   ├── Analytics.tsx
│   │   │   ├── Logs.tsx
│   │   │   └── Settings.tsx
│   │   └── lib/           # Utilities
│   │       ├── api.ts
│   │       └── utils.ts
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── Dockerfile
│
├── terraform/             # Infrastructure as Code
│   ├── main.tf           # Main Terraform configuration
│   ├── variables.tf      # Variable definitions
│   ├── outputs.tf        # Output definitions
│   └── terraform.tfvars.example
│
├── docker-compose.yml     # Local development setup
├── docker-compose.prod.yml # Production setup
├── bitbucket-pipelines.yml # CI/CD pipeline
└── README.md
```

## 🔧 Configuration

### Environment Variables

| Variable                      | Description                    | Default                 |
| ----------------------------- | ------------------------------ | ----------------------- |
| `GCP_PROJECT_ID`              | GCP Project ID                 | -                       |
| `GCP_REGION`                  | GCP Region                     | `us-central1`           |
| `FIRESTORE_COLLECTION_PREFIX` | Firestore collection prefix    | `creative_ads`          |
| `PUBSUB_TOPIC`                | Pub/Sub topic for jobs         | `agentic-ads-jobs`      |
| `PUBSUB_SUBSCRIPTION`         | Pub/Sub subscription           | `agentic-ads-jobs-sub`  |
| `AGENT_API_URL`               | URL of the Agent Brain service | `http://localhost:8081` |
| `SCRAPER_API_URL`             | URL of the Scraper service     | `http://localhost:3001` |
| `VITE_API_URL`                | API URL for frontend           | `http://localhost:8000` |
| `USE_EMULATOR`                | Use GCP emulators              | `false`                 |
| `LOG_LEVEL`                   | Logging level                  | `INFO`                  |

## 🚢 Deployment

### Using Terraform

1. **Configure Terraform variables**

   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

2. **Initialize and apply**
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

### Using Bitbucket Pipelines

The repository includes a complete CI/CD pipeline that:

1. **On feature branches**: Runs linting and tests
2. **On develop branch**: Tests → Build → Deploy to Development
3. **On staging branch**: Tests → Build → Deploy to Staging
4. **On main branch**: Tests → Build → Deploy to Staging → Deploy to Production

#### Required Pipeline Variables

Set these in Bitbucket Repository Settings > Pipelines > Repository Variables:

| Variable                 | Description                                |
| ------------------------ | ------------------------------------------ |
| `GCP_PROJECT_ID`         | GCP Project ID                             |
| `GCP_REGION`             | GCP Region                                 |
| `GCLOUD_SERVICE_KEY`     | Base64-encoded service account key         |
| `ARTIFACT_REGISTRY_REPO` | Artifact Registry repository name          |
| `TERRAFORM_STATE_BUCKET` | GCS bucket for Terraform state             |
| `SLACK_WEBHOOK_URL`      | Slack webhook for notifications (optional) |

### Manual Deployment

```bash
# Build images
docker build -t dashboard-api:latest backend/
docker build -t dashboard-frontend:latest frontend/

# Tag and push to Artifact Registry
docker tag dashboard-api:latest ${REGION}-docker.pkg.dev/${PROJECT_ID}/dashboard/api:latest
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/dashboard/api:latest

# Deploy to Cloud Run
gcloud run deploy dashboard-api \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/dashboard/api:latest \
  --region ${REGION} \
  --platform managed
```

## 📊 API Reference

### Jobs API

| Endpoint                       | Method | Description                  |
| ------------------------------ | ------ | ---------------------------- |
| `/api/v1/jobs`                 | GET    | List all jobs with filtering |
| `/api/v1/jobs/{job_id}`        | GET    | Get job details              |
| `/api/v1/jobs/trigger`         | POST   | Trigger a new pipeline job   |
| `/api/v1/jobs/{job_id}/retry`  | POST   | Retry a failed job           |
| `/api/v1/jobs/{job_id}/stop`   | POST   | Stop a running job           |
| `/api/v1/jobs/{job_id}/pause`  | POST   | Pause a running job          |
| `/api/v1/jobs/{job_id}/resume` | POST   | Resume a paused job          |

### Assets API

| Endpoint                                     | Method | Description                |
| -------------------------------------------- | ------ | -------------------------- |
| `/api/v1/assets`                             | GET    | List assets with filtering |
| `/api/v1/assets/{asset_id}`                  | GET    | Get asset details          |
| `/api/v1/assets/{asset_id}/extract-features` | POST   | Re-run feature extraction  |
| `/api/v1/assets/{asset_id}/generate-prompt`  | POST   | Re-generate reverse prompt |

### Metrics API

| Endpoint                     | Method | Description                       |
| ---------------------------- | ------ | --------------------------------- |
| `/api/v1/metrics/overall`    | GET    | Get overall pipeline metrics      |
| `/api/v1/metrics/queue`      | GET    | Get job queue metrics             |
| `/api/v1/metrics/sources`    | GET    | Get per-source metrics            |
| `/api/v1/metrics/industries` | GET    | Get industry distribution metrics |

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v --cov=app
```

### Frontend Tests

```bash
cd frontend
npm run test
```

## 🔐 Security

- All production deployments require authentication
- Service-to-service communication uses IAM
- Secrets stored in GCP Secret Manager
- CORS configured for allowed origins only
- All traffic over HTTPS

## 📈 Monitoring

The dashboard includes pre-configured Cloud Monitoring:

- **Uptime Checks**: API health monitoring
- **Alert Policies**: Error rate and latency alerts
- **Custom Dashboard**: Request counts, latency, resource utilization

Access the monitoring dashboard in GCP Console or via the dashboard's built-in metrics page.

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Run tests: `npm run test && pytest`
4. Push and create a PR

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.
