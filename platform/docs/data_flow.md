# Data Flow Documentation

## Overview

This document describes the data flow through the Agentic Ads Platform pipeline.

## End-to-End Data Flow

```mermaid
flowchart TB
    subgraph "Input Sources"
        Meta[Meta Ad Library]
        Google[Google Ads Transparency]
        Archive[Internet Archive]
        Wiki[Wikimedia Commons]
    end

    subgraph "Scraping Layer"
        Playwright[Playwright Scrapers]
        RateLimit[Rate Limiter]
        Validator[Data Validator]
    end

    subgraph "Storage Layer"
        RawAssets[(Raw Assets)]
        MetadataDB[(Metadata DB)]
        Queue[(Job Queue)]
    end

    subgraph "Processing Layer"
        FeatureExtract[Feature Extraction]
        Classifier[Industry Classifier]
        PromptGen[Prompt Generator]
    end

    subgraph "Output"
        Dashboard[Web Dashboard]
        API[REST API]
        Export[Data Export]
    end

    Meta --> Playwright
    Google --> Playwright
    Archive --> Playwright
    Wiki --> Playwright

    Playwright --> RateLimit
    RateLimit --> Validator

    Validator -->|Images| RawAssets
    Validator -->|Metadata| MetadataDB
    Validator -->|Job| Queue

    Queue --> FeatureExtract
    FeatureExtract --> MetadataDB

    Queue --> Classifier
    Classifier --> MetadataDB

    Queue --> PromptGen
    PromptGen --> MetadataDB

    MetadataDB --> Dashboard
    MetadataDB --> API
    MetadataDB --> Export
```

## Asset Data Model

```mermaid
erDiagram
    ASSET {
        string id PK
        string source
        string source_url
        string image_url
        string asset_type
        string advertiser_name
        string title
        string description
        datetime scraped_at
        datetime processed_at
    }

    FEATURES {
        string asset_id FK
        string layout_type
        string focal_point
        json dominant_colors
        float brightness
        float contrast
        json typography
        json cta
        json composition
        float quality_score
    }

    CLASSIFICATION {
        string asset_id FK
        string industry
        json industry_tags
        float confidence
    }

    PROMPTS {
        string asset_id FK
        string reverse_prompt
        string negative_prompt
        string generation_method
        json metadata
    }

    JOB {
        string id PK
        string job_type
        string status
        json payload
        int retry_count
        string error_message
        datetime created_at
        datetime completed_at
    }

    ASSET ||--o| FEATURES : has
    ASSET ||--o| CLASSIFICATION : has
    ASSET ||--o| PROMPTS : has
    JOB }o--|| ASSET : processes
```

## Pipeline Stages

### Stage 1: Scraping

```mermaid
sequenceDiagram
    participant Brain as Agent Brain
    participant Queue as Job Queue
    participant Scraper as Playwright
    participant Source as Ad Source
    participant Storage as Storage

    Brain->>Queue: Enqueue Scrape Job
    Queue->>Scraper: Dequeue Job

    activate Scraper
    Scraper->>Source: Navigate to page
    Source-->>Scraper: Page content

    loop For each ad
        Scraper->>Source: Extract ad data
        Source-->>Scraper: Ad metadata + image URL
        Scraper->>Storage: Store raw image
        Storage-->>Scraper: Asset path
        Scraper->>Storage: Store metadata
    end
    deactivate Scraper

    Scraper->>Queue: Enqueue Feature Jobs
    Scraper->>Queue: Mark Job Complete
```

### Stage 2: Feature Extraction

```mermaid
sequenceDiagram
    participant Queue as Job Queue
    participant Extractor as Feature Extractor
    participant Storage as Storage

    Queue->>Extractor: Dequeue Feature Job

    activate Extractor
    Extractor->>Storage: Load image
    Storage-->>Extractor: Image data

    Extractor->>Extractor: Extract colors
    Extractor->>Extractor: Detect layout
    Extractor->>Extractor: Analyze typography
    Extractor->>Extractor: Find CTA
    Extractor->>Extractor: Score quality

    Extractor->>Storage: Store features
    deactivate Extractor

    Extractor->>Queue: Enqueue Classification Job
    Extractor->>Queue: Mark Job Complete
```

### Stage 3: Industry Classification

```mermaid
sequenceDiagram
    participant Queue as Job Queue
    participant Classifier as Industry Classifier
    participant Storage as Storage

    Queue->>Classifier: Dequeue Classification Job

    activate Classifier
    Classifier->>Storage: Load features
    Storage-->>Classifier: Feature data

    Classifier->>Classifier: Keyword matching
    Classifier->>Classifier: Visual heuristics
    Classifier->>Classifier: Score industries

    Classifier->>Storage: Store classification
    deactivate Classifier

    Classifier->>Queue: Enqueue Prompt Job
    Classifier->>Queue: Mark Job Complete
```

### Stage 4: Reverse Prompt Generation

```mermaid
sequenceDiagram
    participant Queue as Job Queue
    participant Gen as Prompt Generator
    participant LLM as LLM Adapter
    participant Storage as Storage

    Queue->>Gen: Dequeue Prompt Job

    activate Gen
    Gen->>Storage: Load features + industry
    Storage-->>Gen: Feature data

    alt Local Mode
        Gen->>LLM: Generate (template)
        LLM->>LLM: Apply rules
        LLM-->>Gen: Deterministic prompt
    else Cloud Mode
        Gen->>LLM: Generate (Vertex AI)
        LLM->>LLM: Call Gemini API
        LLM-->>Gen: AI-generated prompt
    end

    Gen->>Storage: Store prompts
    deactivate Gen

    Gen->>Queue: Mark Job Complete
```

## Data Transformations

### Raw Scrape → Validated Asset

```json
// Input: Raw scrape data
{
  "url": "https://example.com/ad/123",
  "imageUrl": "https://cdn.example.com/ad123.jpg",
  "text": "Shop now and save 50%!",
  "advertiser": "Example Store"
}

// Output: Validated asset
{
  "id": "meta-abc123def456",
  "source": "meta_ad_library",
  "source_url": "https://example.com/ad/123",
  "image_url": "https://cdn.example.com/ad123.jpg",
  "asset_type": "image",
  "advertiser_name": "Example Store",
  "title": "Shop now and save 50%!",
  "raw_asset_path": "./data/assets/raw/meta-abc123def456.jpg",
  "scraped_at": "2024-01-15T10:30:00Z"
}
```

### Asset → Features

```json
// Input: Asset with image
{
  "id": "meta-abc123def456",
  "image_url": "https://cdn.example.com/ad123.jpg"
}

// Output: Extracted features
{
  "asset_id": "meta-abc123def456",
  "layout_type": "hero",
  "focal_point": "product",
  "dominant_colors": [
    {"hex": "#2980b9", "percentage": 0.35},
    {"hex": "#ffffff", "percentage": 0.30}
  ],
  "overall_brightness": 0.72,
  "contrast_level": 0.65,
  "typography": {
    "has_headline": true,
    "estimated_readability": 0.85
  },
  "cta": {
    "detected": true,
    "type": "shop_now",
    "text": "Shop Now"
  },
  "quality_score": 0.88
}
```

### Features → Prompt

```json
// Input: Features + Industry
{
  "features": { /* ... */ },
  "industry": "ecommerce"
}

// Output: Reverse prompt
{
  "positive": "Advertisement creative: large hero image composition, prominent central subject, vibrant, enticing, product showcase, color palette featuring #2980b9, #ffffff, bright, well-lit, focus on product, clear CTA button: 'Shop Now', high quality, professional",
  "negative": "blurry, low quality, distorted, watermark, amateur, dull colors, complex backgrounds",
  "metadata": {
    "generation_method": "template",
    "industry": "ecommerce",
    "confidence": 0.75
  }
}
```

## Storage Schemas

### Local Mode (JSON)

```
data/
├── db/
│   ├── creative_ads_assets.json      # Asset metadata
│   ├── creative_ads_jobs.json        # Job records
│   └── creative_ads_metrics.json     # Aggregated metrics
│
├── assets/
│   ├── raw/                          # Original images
│   │   ├── meta-abc123.jpg
│   │   └── google-xyz789.png
│   │
│   └── processed/                    # Processed images
│       └── meta-abc123.webp
│
├── logs/
│   ├── logs_20240115.json
│   └── logs_20240116.json
│
└── metrics/
    └── metrics_20240115.json
```

### Cloud Mode (GCP)

```
Firestore:
├── creative_ads_assets/              # Asset documents
├── creative_ads_jobs/                # Job documents
└── creative_ads_metrics/             # Metric documents

Cloud Storage:
├── {project}-raw-assets/
│   └── assets/
│       └── meta-abc123.jpg
│
└── {project}-processed-assets/
    └── processed/
        └── meta-abc123.webp

Pub/Sub:
├── agentic-ads-jobs                 # Main job topic
├── agentic-ads-jobs-sub             # Subscription
└── agentic-ads-jobs-dlq             # Dead letter queue
```
