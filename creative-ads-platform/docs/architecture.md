# System Architecture

## Overview

The Creative Ads Platform is a **local-first, cloud-optional agentic system** for scraping, analyzing, and generating reverse prompts for creative advertisements.

## Architecture Diagram

```mermaid
graph TB
    subgraph "Entry Points"
        CLI[CLI Interface]
        API[REST API]
        Dashboard[Web Dashboard]
    end

    subgraph "Orchestration Layer"
        Orchestrator[Orchestrator<br/>Mode Detection & DI]
        Config[Config Manager<br/>MODE=local/cloud]
    end

    subgraph "Agent Core"
        Brain[Agent Brain<br/>Orchestration]
        Pipeline[Pipeline Manager]
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
        Scraper[Playwright Scrapers<br/>Node.js]
        FeatureExtract[Feature Extraction<br/>Python]
        Classifier[Industry Classifier]
        ReversePrompt[Reverse Prompt<br/>Generator]
    end

    CLI --> Orchestrator
    API --> Orchestrator
    Dashboard --> Orchestrator

    Orchestrator --> Config
    Orchestrator --> Brain
    Config -->|Injects| IStorage
    Config -->|Injects| IQueue
    Config -->|Injects| ILLM
    Config -->|Injects| IMonitor

    Brain --> Pipeline
    Pipeline --> Scraper
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
```

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

| Component | LOCAL MODE | CLOUD MODE |
|-----------|------------|------------|
| Agent Brain | Local Python | Cloud Run |
| Scrapers | Local Node.js | Cloud Run |
| Storage (Documents) | JSON Files | Firestore |
| Storage (Files) | Local FS | Cloud Storage |
| Queue | In-Memory | Pub/Sub |
| Reverse Prompt | Templates/Ollama | **Vertex AI** |
| Monitoring | Local Logs + UI | Cloud Monitoring |
| Auth | Disabled | IAM |

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Dashboard
    participant Brain as Agent Brain
    participant Queue
    participant Scraper
    participant Extract as Feature Extraction
    participant LLM
    participant Storage

    User->>Dashboard: Start Scraping Job
    Dashboard->>Brain: Create Job Request
    Brain->>Queue: Enqueue Scrape Job
    
    loop For Each Source
        Queue->>Scraper: Dequeue Job
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
    
    Storage->>Dashboard: Update UI
    Dashboard->>User: Show Results
```

## Directory Structure

```
creative-ads-platform/
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
│   ├── agent_brain.py       # Core orchestration
│   ├── orchestrator.py      # DI container
│   └── config.py            # Configuration
│
├── scrapers/                # Node.js Playwright scrapers
├── feature_extraction/      # Python feature extraction
├── reverse_prompt/          # Prompt generation
│   ├── rules_engine.py      # Template-based
│   └── templates/           # Industry templates
├── dashboard/               # Web UI
├── docs/                    # Documentation
└── data/                    # Local data storage
```

