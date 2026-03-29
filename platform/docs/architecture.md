# System Architecture

## Overview

The Agentic Ads Platform is a **local-first, cloud-optional agentic system** for scraping, analyzing, and generating reverse prompts for creative advertisements. It features **real-time live streaming** of browser sessions for monitoring scraper activity.

## Architecture Diagram

```mermaid
graph TB
    subgraph "Frontend"
        Dashboard[Web Dashboard<br/>localhost:5173]
    end

    subgraph "Backend Services"
        DashboardAPI[Dashboard Backend<br/>localhost:8000]
        AgentAPI[Agent API<br/>localhost:8080]
        ScraperServer[Node.js Scraper<br/>localhost:3001]
    end

    subgraph "Orchestration Layer"
        Orchestrator[Orchestrator<br/>Mode Detection & DI]
        Config[Config Manager<br/>MODE=local/cloud]
    end

    subgraph "Agent Core"
        Brain[Agent Brain<br/>Orchestration]
        Pipeline[Pipeline Manager]
    end

    subgraph "Live Streaming"
        StreamMgr[StreamManager<br/>CDP Screencast]
        WSServer[WebSocket Server<br/>ws://localhost:3001]
        Screenshots[Screenshot Saver<br/>./data/screenshots/]
    end

    subgraph "Interfaces - NEVER import cloud SDKs directly"
        IStorage[StorageInterface]
        IQueue[QueueInterface]
        ILLM[LLMInterface]
        IMonitor[MonitoringInterface]
    end

    subgraph "Local Adapters - MODE=local"
        LocalStorage[LocalStorage<br/>JSON + Filesystem]
        LocalQueue[LocalQueue<br/>In-Memory]
        LocalLLM[LocalLLM<br/>Templates + Ollama]
        LocalMonitor[LocalMonitoring<br/>Files + Logs]
    end

    subgraph "Cloud Adapters - MODE=cloud"
        Firestore[FirestoreStorage<br/>Cloud Firestore]
        PubSub[PubSubQueue<br/>Cloud Pub/Sub]
        VertexLLM[VertexLLM<br/>Vertex AI ONLY]
        CloudMonitor[CloudMonitoring<br/>Cloud Monitoring]
    end

    subgraph "Processing Pipeline"
        Browser[Playwright Browser<br/>Chromium]
        FeatureExtract[Feature Extraction<br/>Python]
        Classifier[Industry Classifier]
        ReversePrompt[Reverse Prompt<br/>Generator]
    end

    Dashboard -->|HTTP| DashboardAPI
    Dashboard -.->|WebSocket| WSServer
    DashboardAPI -->|HTTP| AgentAPI
    AgentAPI -->|HTTP| ScraperServer

    AgentAPI --> Orchestrator
    Orchestrator --> Config
    Orchestrator --> Brain
    Config -->|Injects| IStorage
    Config -->|Injects| IQueue
    Config -->|Injects| ILLM
    Config -->|Injects| IMonitor

    Brain --> Pipeline
    ScraperServer --> Browser
    ScraperServer --> StreamMgr
    StreamMgr --> WSServer
    StreamMgr --> Screenshots
    Browser -->|CDP frames| StreamMgr
    Pipeline --> FeatureExtract
    Pipeline --> Classifier
    Pipeline --> ReversePrompt

    IStorage -.->|local| LocalStorage
    IStorage -.->|cloud| Firestore
    IQueue -.->|local| LocalQueue
    IQueue -.->|cloud| PubSub
    ILLM -.->|local| LocalLLM
    ILLM -.->|cloud| VertexLLM
    IMonitor -.->|local| LocalMonitor
    IMonitor -.->|cloud| CloudMonitor

    style VertexLLM fill:#ff6b6b,stroke:#c92a2a,stroke-width:3px
    style LocalLLM fill:#69db7c,stroke:#2f9e44,stroke-width:2px
    style Orchestrator fill:#4dabf7,stroke:#1971c2,stroke-width:2px
    style WSServer fill:#be4bdb,stroke:#862e9c,stroke-width:2px
    style StreamMgr fill:#be4bdb,stroke:#862e9c,stroke-width:2px
```

## Service Ports

| Service            | Port | Protocol  | Purpose                   |
| ------------------ | ---- | --------- | ------------------------- |
| Dashboard Frontend | 5173 | HTTP      | React UI                  |
| Dashboard Backend  | 8000 | HTTP      | API proxy, SSE events     |
| Agent API          | 8080 | HTTP      | Job orchestration         |
| Node.js Scraper    | 3001 | HTTP + WS | Scraping + live streaming |

## Key Design Principles

### 1. Local-First Development

The platform is designed to run **completely offline** without any cloud dependencies:

- All GCP services are emulated locally
- No GCP credentials required for local development
- Full functionality available on low-RAM machines

### 2. Strict Adapter Boundaries

**Business logic NEVER imports cloud SDKs directly.**

```python
# ❌ WRONG - Direct cloud import in business logic
from google.cloud import firestore
client = firestore.Client()

# ✅ CORRECT - Interface import, adapter injected
from agent.interfaces import StorageInterface

class MyService:
    def __init__(self, storage: StorageInterface):
        self.storage = storage
```

### 3. Vertex AI is CLOUD-ONLY

```mermaid
flowchart LR
    subgraph "LOCAL MODE"
        L1[Templates] --> L2[Deterministic Prompts]
        L3[Ollama] --> L4[Local AI Prompts]
    end

    subgraph "CLOUD MODE"
        C1[Vertex AI] --> C2[AI-Generated Prompts]
    end

    MODE{MODE=?}
    MODE -->|local| L1
    MODE -->|local + ollama| L3
    MODE -->|cloud| C1

    X[Vertex AI in Local] -->|BLOCKED| Error[RuntimeError]

    style C1 fill:#ff6b6b,stroke:#c92a2a,stroke-width:3px
    style X fill:#ff6b6b,stroke:#c92a2a,stroke-width:2px
    style Error fill:#ff6b6b,stroke:#c92a2a
```

## Component Map

| Component           | LOCAL MODE                | CLOUD MODE          |
| ------------------- | ------------------------- | ------------------- |
| Dashboard Frontend  | Vite dev server           | Cloud Run / GCS     |
| Dashboard Backend   | Uvicorn                   | Cloud Run           |
| Agent Brain         | Local Python              | Cloud Run           |
| Scrapers            | Local Node.js + WebSocket | Cloud Run           |
| Live Streaming      | CDP Screencast + WS       | CDP Screencast + WS |
| Storage (Documents) | JSON Files                | Firestore           |
| Storage (Files)     | Local FS                  | Cloud Storage       |
| Screenshots         | ./data/screenshots/       | Cloud Storage       |
| Queue               | In-Memory                 | Pub/Sub             |
| Reverse Prompt      | Templates/Ollama          | **Vertex AI**       |
| Monitoring          | Local Logs + UI           | Cloud Monitoring    |
| Auth                | Disabled                  | IAM                 |

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Dashboard
    participant DashAPI as Dashboard Backend
    participant Agent as Agent API
    participant Brain as Agent Brain
    participant Queue
    participant Scraper as Node.js Scraper
    participant Browser as Playwright
    participant Extract as Feature Extraction
    participant LLM
    participant Storage

    User->>Dashboard: Click "Scrape Assets"
    Dashboard->>DashAPI: POST /api/v1/jobs
    DashAPI->>Agent: Forward job request
    Agent->>Brain: Create Job Request
    Brain->>Queue: Enqueue Scrape Job
    Queue->>Scraper: POST /scrape (streaming=true)
    Scraper->>Browser: Launch Chromium
    Scraper->>Scraper: Start CDP Screencast

    Dashboard->>Scraper: WebSocket connect
    Note over Dashboard,Scraper: ws://localhost:3001/ws/stream

    loop Every CDP Frame
        Browser-->>Scraper: screencastFrame event
        Scraper-->>Dashboard: WebSocket frame (base64 JPEG)
        Scraper->>Storage: Save periodic screenshot
    end

    loop For Each Source
        Scraper->>Storage: Store Raw Assets
        Scraper->>Queue: Enqueue Extract Job
    end

    loop For Each Asset
        Queue->>Extract: Dequeue Job
        Extract->>Storage: Store Features
        Extract->>Queue: Enqueue Prompt Job
    end

    loop For Each Feature Set
        Queue->>LLM: Dequeue Job
        alt Local Mode
            LLM->>LLM: Template Generation
        else Cloud Mode
            LLM->>LLM: Vertex AI Generation
        end
        LLM->>Storage: Store Prompts
    end

    Agent-->>Dashboard: SSE job_completed event
    Dashboard->>User: Show results + replay available
```

## Live Streaming Architecture

```mermaid
flowchart LR
    subgraph "Dashboard Frontend"
        UI[React UI]
        Hook[useScraperStream]
        Viewer[ScraperViewer]
        Replay[JobReplayPlayer]
    end

    subgraph "Node.js Scraper Server :3001"
        HTTP[HTTP API]
        WS[WebSocket Server]
        SM[StreamManager]
        SS[ScreenshotSaver]
    end

    subgraph "Browser"
        PW[Playwright]
        CDP[CDP Session]
    end

    subgraph "Storage"
        FS[./data/screenshots/]
    end

    UI -->|trigger job| HTTP
    Hook <-->|frames| WS
    WS <--> SM
    SM <-->|screencast| CDP
    CDP <--> PW
    SM -->|periodic| SS
    SS --> FS
    Replay -->|load| FS
    Hook --> Viewer

    style WS fill:#be4bdb
    style SM fill:#be4bdb
```

### Streaming Modes

| Mode       | Headless | Streaming | Use Case                      |
| ---------- | -------- | --------- | ----------------------------- |
| Production | `true`   | `true`    | Monitor scraping in dashboard |
| Debug      | `false`  | `false`   | Watch visible browser window  |
| Silent     | `true`   | `false`   | Fastest scraping, no overhead |

## Directory Structure

```
agentic-ads-platform/
├── agent/
│   ├── interfaces/          # Abstract interfaces (contracts)
│   │   ├── storage.py       # StorageInterface
│   │   ├── queue.py         # QueueInterface
│   │   ├── llm.py           # LLMInterface
│   │   └── monitoring.py    # MonitoringInterface
│   │
│   ├── adapters/
│   │   ├── local/           # Local implementations
│   │   │   ├── local_storage.py
│   │   │   ├── local_queue.py
│   │   │   ├── local_llm.py
│   │   │   └── local_monitoring.py
│   │   │
│   │   └── cloud/           # Cloud implementations
│   │       ├── firestore_storage.py
│   │       ├── pubsub_queue.py
│   │       ├── vertex_llm.py    # CLOUD ONLY!
│   │       └── cloud_monitoring.py
│   │
│   ├── services/            # Agent services
│   │   ├── stream_manager.py    # Live streaming (Python)
│   │   └── screenshot_saver.py  # Replay screenshots
│   │
│   ├── agent_brain.py       # Core orchestration
│   ├── orchestrator.py      # DI container
│   ├── api.py               # FastAPI endpoints (port 8080)
│   └── config.py            # Configuration
│
├── scrapers/                # Node.js Playwright scrapers
│   ├── scraper.js           # Base scraper + source scrapers
│   ├── server.js            # HTTP + WebSocket server (port 3001)
│   ├── streaming.js         # CDP screencast + StreamManager
│   └── utils.js             # Shared utilities
│
├── dashboard/
│   ├── backend/             # FastAPI backend (port 8000)
│   │   └── app/
│   │       ├── routers/
│   │       │   ├── jobs.py
│   │       │   ├── scrapers.py  # Proxies to Node.js scraper
│   │       │   └── events.py    # SSE for real-time updates
│   │       └── services/
│   │
│   └── frontend/            # React + Vite (port 5173)
│       └── src/
│           ├── components/
│           │   ├── ScraperViewer.tsx   # Live video player
│           │   ├── ScraperGrid.tsx     # Multi-scraper view
│           │   └── JobReplayPlayer.tsx # Screenshot replay
│           ├── hooks/
│           │   ├── useScraperStream.ts # WebSocket hook
│           │   ├── useJobScreenshots.ts
│           │   └── useEventStream.ts   # SSE hook
│           └── pages/
│               └── Pipeline.tsx        # Control + Live View
│
├── feature_extraction/      # Python feature extraction
├── reverse_prompt/          # Prompt generation
│   ├── rules_engine.py      # Template-based
│   └── templates/           # Industry templates
├── docs/                    # Documentation
└── data/                    # Local data storage
    ├── db/                  # JSON databases
    ├── screenshots/         # Scraper screenshots by session
    ├── logs/                # Pipeline logs
    └── metrics/             # System metrics
```
