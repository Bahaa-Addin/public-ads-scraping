# Public Ads Platform

A **local-first, cloud-optional agentic system** for scraping creative advertisements, extracting features, classifying industries, and generating reverse prompts.

This directory contains the main application source for the public repository. Use [`../README.md`](../README.md) for the repository-level overview and governance docs.



## 🎯 Key Features

- **Local-First**: Runs completely offline without cloud dependencies
- **Cloud-Ready**: Seamless deployment to GCP when needed
- **Low-RAM Optimized**: Runs on machines with limited resources
- **Explainable**: Every decision is traceable and reproducible
- **Zero Cloud Costs Locally**: No API calls, no charges during development

## ⚡ Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (optional, for containerized setup)

### Local Setup (5 minutes)

```bash
# Clone and navigate to project
cd platform

# Optional bootstrap: creates data folders and a local .env file
./scripts/setup.sh --quick

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies for scrapers
cd scrapers && npm install && cd ..

# Copy example environment
cp env.example .env

# Run in local mode (default)
python main.py
```

### Environment Variables

Create a `.env` file from the example and keep the real file out of git:

```bash
cp env.example .env
```

Minimal local settings:

```bash
# Mode: 'local' (default) or 'cloud'
MODE=local

# Local storage
DATA_DIR=./data

# LLM mode: 'template' (default) or 'ollama'
LLM_MODE=template

# Low-RAM settings (defaults are conservative)
MAX_BROWSER_INSTANCES=1
SEQUENTIAL_SCRAPING=true
GLOBAL_JOB_CAP=100

# Logging
LOG_LEVEL=INFO
```

## 📦 Project Structure

```
platform/
├── agent/
│   ├── interfaces/           # Abstract contracts (NEVER import cloud SDKs)
│   │   ├── storage.py
│   │   ├── queue.py
│   │   ├── llm.py
│   │   └── monitoring.py
│   │
│   ├── adapters/
│   │   ├── local/            # Local implementations (MODE=local)
│   │   │   ├── local_storage.py
│   │   │   ├── local_queue.py
│   │   │   ├── local_llm.py
│   │   │   └── local_monitoring.py
│   │   │
│   │   └── cloud/            # Cloud implementations (MODE=cloud)
│   │       ├── firestore_storage.py
│   │       ├── pubsub_queue.py
│   │       ├── vertex_llm.py      # ⚠️ CLOUD ONLY!
│   │       └── cloud_monitoring.py
│   │
│   ├── agent_brain.py        # Core orchestration
│   ├── orchestrator.py       # Dependency injection
│   └── config.py             # Configuration
│
├── scrapers/                 # Node.js Playwright scrapers
├── feature_extraction/       # Python feature extraction
├── reverse_prompt/           # Prompt generation
│   ├── rules_engine.py       # Deterministic templates
│   └── templates/            # Industry templates
├── dashboard/                # Web UI
├── docs/                     # Architecture diagrams
├── terraform/                # Cloud infrastructure (cloud only)
└── docker/                   # Container configs
```

## 🔄 Modes

### Local Mode (Default)

```bash
MODE=local python main.py
```

| Component | Implementation |
|-----------|---------------|
| Storage | JSON files (`./data/db/`) |
| Files | Local filesystem (`./data/assets/`) |
| Queue | In-memory |
| LLM | **Templates** or **Ollama** |
| Monitoring | Local logs + files |

### Cloud Mode

```bash
MODE=cloud \
GCP_PROJECT_ID=your-project \
python main.py
```

| Component | Implementation |
|-----------|---------------|
| Storage | Cloud Firestore |
| Files | Cloud Storage |
| Queue | Cloud Pub/Sub |
| LLM | **Vertex AI (Gemini)** |
| Monitoring | Cloud Monitoring |

## ⚠️ CRITICAL: Vertex AI is CLOUD-ONLY

**Vertex AI can ONLY be used in cloud mode.**

```python
# This will FAIL in local mode:
MODE=local LLM_MODE=vertex python main.py
# -> VertexAINotAvailableError

# Local alternatives:
MODE=local LLM_MODE=template python main.py  # Deterministic templates
MODE=local LLM_MODE=ollama python main.py    # Local Ollama AI
```

The restriction ensures:
- **Zero cloud costs** during development
- **Reproducible outputs** for testing
- **Offline capability** for all development work

## 🐳 Docker Setup

### Basic (Recommended for Low-RAM)

```bash
# Start core services
docker-compose up

# Access dashboard at http://localhost:8080
# API available at http://localhost:8081
```

### With Firebase Emulators

```bash
docker-compose --profile emulators up
```

### With Local AI (Ollama)

```bash
# Requires 8GB+ RAM
docker-compose --profile ollama up

# Pull a model
docker exec -it creative-ads-platform_ollama_1 ollama pull llama2
```

## 🔧 Low-RAM Configuration

The platform is optimized for machines with limited resources:

```bash
# Conservative settings (default)
MAX_BROWSER_INSTANCES=1      # Single browser
SEQUENTIAL_SCRAPING=true     # No parallel scraping
GLOBAL_JOB_CAP=100           # Limit total jobs
MAX_QUEUE_SIZE=1000          # Queue limit
MAX_ASSETS_IN_MEMORY=50      # Memory limit
IMAGE_ONLY_MODE=true         # Skip video processing
```

Minimum requirements:
- **CPU**: 2 cores
- **RAM**: 2GB (4GB recommended)
- **Disk**: 10GB free

## 📊 Dashboard

The web dashboard provides:

### Controls
- Start/stop scraping
- Select data sources
- Job limits configuration
- Throttle settings
- Toggle AI inference on/off

### Observability
- Job state per pipeline stage
- Feature extraction output
- Industry classification
- Reverse prompt preview
- Error traces

### Debug Panels
- Raw asset preview
- Feature JSON
- Prompt + negative prompt
- Local vs Cloud diff

Access at: `http://localhost:8080`

## 🚀 Cloud Deployment

### Prerequisites

1. GCP Project with billing enabled
2. Enable APIs: Firestore, Pub/Sub, Cloud Storage, Vertex AI
3. Service account with appropriate permissions

### Deploy with Terraform

```bash
cd terraform

# Initialize
terraform init

# Plan
terraform plan -var="project_id=your-project-id"

# Apply
terraform apply -var="project_id=your-project-id"
```

### Cost Control

- Vertex AI: ~$0.002 per prompt generation
- Firestore: Free tier covers most dev usage
- Pub/Sub: Free tier covers most dev usage
- Cloud Storage: ~$0.02/GB/month

**Estimated monthly cost for moderate usage: $20-50**

### Scaling Strategy

| Load | Configuration |
|------|---------------|
| Light | Single Cloud Run instance |
| Medium | 2-3 instances, autoscaling |
| Heavy | Horizontal scaling, dedicated VMs |

## 📚 Documentation

- [Architecture](docs/architecture.md) - System design and diagrams
- [State Machine](docs/state_machine.md) - Pipeline state flows
- [Local vs Cloud](docs/local_vs_cloud.md) - Mode comparison
- [Data Flow](docs/data_flow.md) - Data transformations

## 🧪 Testing

```bash
# Run tests in local mode (fast, deterministic)
MODE=local pytest tests/

# Run specific test suite
pytest tests/test_adapters.py -v

# Run with coverage
pytest --cov=agent tests/
```

## 🤝 Contributing

See [`../CONTRIBUTING.md`](../CONTRIBUTING.md) for setup, testing, and pull request expectations.

### Code Quality Rules

- **NO cloud SDK imports in business logic**
- **NO Vertex AI usage in local mode**
- **ALL features must work offline**
- **EVERY component must be testable locally**

## 📄 License

MIT License - see [`../LICENSE`](../LICENSE)

## 🆘 Troubleshooting

### "Vertex AI not available"

You're trying to use Vertex AI in local mode. Set `MODE=cloud` or use `LLM_MODE=template`.

### "Out of memory"

Reduce resource limits:
```bash
MAX_BROWSER_INSTANCES=1
MAX_ASSETS_IN_MEMORY=20
GLOBAL_JOB_CAP=50
```

### "Scraper timeout"

Increase timeout or reduce load:
```bash
PAGE_TIMEOUT_MS=60000
REQUEST_DELAY_MS=2000
```

### "Firebase emulator connection failed"

Ensure emulators are running:
```bash
docker-compose --profile emulators up
```

---

Built with ❤️ for offline-first, privacy-respecting development.
