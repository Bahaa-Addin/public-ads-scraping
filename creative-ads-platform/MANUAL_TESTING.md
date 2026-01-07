# Creative Ads Platform - Hands-On Manual Testing Guide

> **Purpose**: This guide walks you through manually testing every component that has been built, with interactive examples and expected outputs.

---

## 📍 Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Testing Configuration System](#2-testing-configuration-system)
3. [Testing Local Storage Adapter](#3-testing-local-storage-adapter)
4. [Testing Local Queue Adapter](#4-testing-local-queue-adapter)
5. [Testing Local LLM Adapter](#5-testing-local-llm-adapter)
6. [Testing Local Monitoring Adapter](#6-testing-local-monitoring-adapter)
7. [Testing the Orchestrator](#7-testing-the-orchestrator)
8. [Testing the Agent Brain](#8-testing-the-agent-brain)
9. [Testing the Agent API](#9-testing-the-agent-api)
10. [Testing the Dashboard Backend](#10-testing-the-dashboard-backend)
11. [Testing the Dashboard Frontend](#11-testing-the-dashboard-frontend)
12. [End-to-End Integration Test](#12-end-to-end-integration-test)

---

## 1. Environment Setup

### 1.1 Open Terminal and Navigate

```bash
cd /Users/monterey/Workspace/Projs/Tasmem/tasmem-scraping/creative-ads-platform
```

### 1.2 Set Required Environment Variables

```bash
export MODE=local
export DATA_DIR=./data
export LLM_MODE=template
```

### 1.3 Verify Python Environment

```bash
./venv/bin/python --version
# Expected: Python 3.13.2 (or 3.9+)
```

### 1.4 Quick Validation

```bash
./venv/bin/python scripts/validate.py
```

**✅ Expected**: All checks pass

---

## 2. Testing Configuration System

### 2.1 Load and Inspect Configuration

```bash
./venv/bin/python << 'EOF'
from agent.config import Config, Mode

# Load from environment
config = Config.from_environment()

print("=" * 60)
print("CONFIGURATION TEST")
print("=" * 60)
print(f"Mode:           {config.mode.value}")
print(f"Is Local:       {config.is_local}")
print(f"Is Cloud:       {config.is_cloud}")
print(f"Data Dir:       {config.data_dir}")
print(f"LLM Mode:       {config.llm_mode}")
print(f"Log Level:      {config.log_level}")
print()
print("Low-RAM Settings:")
print(f"  Max Browser:  {config.low_ram.max_browser_instances}")
print(f"  Sequential:   {config.low_ram.sequential_scraping}")
print(f"  Job Cap:      {config.low_ram.global_job_cap}")
print()
print("Validation:")
errors = config.validate()
if errors:
    print(f"  ❌ Errors: {errors}")
else:
    print("  ✅ Configuration valid!")
EOF
```

### 2.2 Test Mode Switching Prevention

```bash
# This should FAIL - Vertex AI not allowed in local mode
LLM_MODE=vertex ./venv/bin/python -c "from agent.config import Config; Config.from_environment()" 2>&1 | head -5
# Expected: ValueError about Vertex not allowed in local mode
```

---

## 3. Testing Local Storage Adapter

### 3.1 Basic CRUD Operations

```bash
./venv/bin/python << 'EOF'
import asyncio
from agent.adapters.local.local_storage import LocalStorage

async def test_storage():
    print("=" * 60)
    print("LOCAL STORAGE ADAPTER TEST")
    print("=" * 60)
    
    # Initialize
    storage = LocalStorage(data_dir="./data", collection_prefix="test")
    await storage.connect()
    print("✅ Connected to local storage")
    
    # Health check
    healthy = await storage.health_check()
    print(f"✅ Health check: {healthy}")
    
    # Store an asset
    asset_data = {
        "source": "manual_test",
        "image_url": "https://example.com/test.jpg",
        "title": "Test Creative Ad",
        "advertiser_name": "Test Advertiser",
        "industry": "technology"
    }
    asset_id = await storage.store_asset("manual-test-001", asset_data)
    print(f"✅ Stored asset: {asset_id}")
    
    # Retrieve asset
    asset = await storage.get_asset("manual-test-001")
    print(f"✅ Retrieved asset: {asset.title}")
    
    # Update asset
    await storage.update_asset("manual-test-001", {"title": "Updated Title"})
    updated = await storage.get_asset("manual-test-001")
    print(f"✅ Updated asset title: {updated.title}")
    
    # Query assets
    results = await storage.query_assets(source="manual_test")
    print(f"✅ Query returned {len(results)} assets")
    
    # Count assets
    count = await storage.count_assets(source="manual_test")
    print(f"✅ Asset count: {count}")
    
    # Test file upload
    test_data = b"Hello, this is test file content!"
    file_path = await storage.upload_file("test-file-001", test_data, "text/plain", "raw")
    print(f"✅ Uploaded file to: {file_path}")
    
    # Download file
    downloaded = await storage.download_file(file_path)
    print(f"✅ Downloaded file: {len(downloaded)} bytes")
    
    # Delete file
    deleted = await storage.delete_file(file_path)
    print(f"✅ Deleted file: {deleted}")
    
    # Delete asset
    await storage.delete_asset("manual-test-001")
    print("✅ Deleted test asset")
    
    # Cleanup
    await storage.close()
    print("✅ Storage closed")
    
    print()
    print("🎉 ALL STORAGE TESTS PASSED!")

asyncio.run(test_storage())
EOF
```

---

## 4. Testing Local Queue Adapter

### 4.1 Job Queue Operations

```bash
./venv/bin/python << 'EOF'
import asyncio
from agent.adapters.local.local_queue import LocalQueue
from agent.interfaces.queue import JobType

async def test_queue():
    print("=" * 60)
    print("LOCAL QUEUE ADAPTER TEST")
    print("=" * 60)
    
    # Initialize
    queue = LocalQueue(max_size=100)
    await queue.connect()
    print("✅ Connected to local queue")
    
    # Health check
    healthy = await queue.health_check()
    print(f"✅ Health check: {healthy}")
    
    # Create scraping job
    job1 = await queue.create_scrape_job(
        source="meta_ad_library",
        query="technology ads"
    )
    print(f"✅ Created scrape job: {job1[:8]}...")
    
    # Create feature extraction job
    job2 = await queue.create_feature_extraction_job(
        asset_id="asset-001",
        asset_url="https://example.com/image.jpg"
    )
    print(f"✅ Created feature job: {job2[:8]}...")
    
    # Create prompt generation job
    job3 = await queue.create_prompt_generation_job(
        asset_id="asset-001",
        features={"layout": "hero", "colors": ["blue", "white"]},
        industry="ecommerce"
    )
    print(f"✅ Created prompt job: {job3[:8]}...")
    
    # Check queue size
    size = queue.get_queue_size()
    print(f"✅ Queue size: {size}")
    
    # Get metrics
    metrics = queue.get_metrics()
    print(f"✅ Metrics:")
    print(f"   Total jobs:    {metrics.total_jobs}")
    print(f"   Pending:       {metrics.pending_jobs}")
    print(f"   In progress:   {metrics.in_progress_jobs}")
    print(f"   Completed:     {metrics.completed_jobs}")
    
    # Dequeue a job
    job = await queue.dequeue(timeout=1.0)
    if job:
        print(f"✅ Dequeued job: {job.job_type.value}")
        
        # Complete the job
        await queue.complete_job(job.id, {"status": "success"})
        print(f"✅ Completed job: {job.id[:8]}...")
    
    # Cleanup
    await queue.close()
    print("✅ Queue closed")
    
    print()
    print("🎉 ALL QUEUE TESTS PASSED!")

asyncio.run(test_queue())
EOF
```

---

## 5. Testing Local LLM Adapter

### 5.1 Template-Based Prompt Generation

```bash
./venv/bin/python << 'EOF'
import asyncio
from agent.adapters.local.local_llm import LocalLLM
from agent.interfaces.llm import PromptStyle

async def test_llm():
    print("=" * 60)
    print("LOCAL LLM ADAPTER TEST")
    print("=" * 60)
    
    # Initialize
    llm = LocalLLM(use_ollama=False)  # Template mode
    await llm.connect()
    print("✅ Connected to local LLM (template mode)")
    
    # Health check
    healthy = await llm.health_check()
    print(f"✅ Health check: {healthy}")
    
    # Test features for different industries
    test_cases = [
        {
            "features": {
                "layout_type": "hero",
                "dominant_colors": [{"hex": "#2980b9", "percentage": 0.4}],
                "overall_brightness": 0.7,
                "focal_point": "product",
                "cta": {"detected": True, "text": "Shop Now"}
            },
            "industry": "ecommerce"
        },
        {
            "features": {
                "layout_type": "split",
                "dominant_colors": [{"hex": "#27ae60", "percentage": 0.5}],
                "overall_brightness": 0.6,
                "focal_point": "data",
                "typography": {"has_headline": True}
            },
            "industry": "finance"
        },
        {
            "features": {
                "layout_type": "minimal",
                "dominant_colors": [{"hex": "#9b59b6", "percentage": 0.3}],
                "overall_brightness": 0.5,
                "focal_point": "interface"
            },
            "industry": "saas"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test['industry'].upper()} ---")
        
        result = await llm.generate_prompt(
            features=test["features"],
            industry=test["industry"],
            style=PromptStyle.DETAILED
        )
        
        print(f"Positive prompt ({len(result.positive)} chars):")
        print(f"  \"{result.positive[:100]}...\"")
        print(f"Negative prompt: \"{result.negative[:50]}...\"")
        print(f"Confidence: {result.confidence}")
        print(f"Method: {result.generation_method}")
    
    # Cleanup
    await llm.close()
    print("\n✅ LLM closed")
    
    print()
    print("🎉 ALL LLM TESTS PASSED!")

asyncio.run(test_llm())
EOF
```

---

## 6. Testing Local Monitoring Adapter

### 6.1 Metrics and Logging

```bash
./venv/bin/python << 'EOF'
import asyncio
from agent.adapters.local.local_monitoring import LocalMonitoring
from agent.interfaces.monitoring import MetricType, LogLevel

async def test_monitoring():
    print("=" * 60)
    print("LOCAL MONITORING ADAPTER TEST")
    print("=" * 60)
    
    # Initialize
    monitoring = LocalMonitoring(log_dir="./data/logs")
    await monitoring.connect()
    print("✅ Connected to local monitoring")
    
    # Health check
    healthy = await monitoring.health_check()
    print(f"✅ Health check: {healthy}")
    
    # Record some metrics
    await monitoring.record_metric(
        name="assets_scraped",
        value=42,
        metric_type=MetricType.COUNTER,
        labels={"source": "meta_ad_library"}
    )
    print("✅ Recorded counter metric")
    
    await monitoring.record_metric(
        name="processing_time",
        value=1.5,
        metric_type=MetricType.HISTOGRAM,
        labels={"stage": "feature_extraction"}
    )
    print("✅ Recorded histogram metric")
    
    await monitoring.record_metric(
        name="queue_size",
        value=10,
        metric_type=MetricType.GAUGE,
        labels={"queue": "main"}
    )
    print("✅ Recorded gauge metric")
    
    # Log messages at different levels
    await monitoring.log(LogLevel.INFO, "Test info message", {"test": True})
    await monitoring.log(LogLevel.WARNING, "Test warning message")
    await monitoring.log(LogLevel.ERROR, "Test error message", {"code": 500})
    print("✅ Logged messages at INFO, WARNING, ERROR levels")
    
    # Get metrics summary
    summary = await monitoring.get_metrics_summary()
    print(f"✅ Metrics summary: {len(summary)} entries")
    for name, data in list(summary.items())[:3]:
        print(f"   {name}: {data}")
    
    # Cleanup
    await monitoring.close()
    print("✅ Monitoring closed")
    
    print()
    print("🎉 ALL MONITORING TESTS PASSED!")

asyncio.run(test_monitoring())
EOF
```

---

## 7. Testing the Orchestrator

### 7.1 Full Orchestrator Lifecycle

```bash
./venv/bin/python << 'EOF'
import asyncio
from agent.config import Config
from agent.orchestrator import Orchestrator

async def test_orchestrator():
    print("=" * 60)
    print("ORCHESTRATOR TEST")
    print("=" * 60)
    
    # Load config
    config = Config.from_environment()
    print(f"✅ Config loaded (mode={config.mode.value})")
    
    # Create orchestrator
    orch = Orchestrator(config)
    print("✅ Orchestrator created")
    
    # Initialize
    await orch.initialize()
    print("✅ Orchestrator initialized")
    
    # Access adapters
    storage = orch.get_storage()
    queue = orch.get_queue()
    llm = orch.get_llm()
    monitoring = orch.get_monitoring()
    print("✅ All adapters accessible")
    
    # Get agent
    agent = orch.get_agent()
    print(f"✅ AgentBrain accessible: {type(agent).__name__}")
    
    # Health check
    health = await orch.health_check()
    print(f"✅ Health check:")
    print(f"   Mode:    {health['mode']}")
    print(f"   Healthy: {health['healthy']}")
    for comp, status in health['components'].items():
        print(f"   {comp}: {'✓' if status else '✗'}")
    
    # Test cross-adapter workflow
    print("\n--- Cross-Adapter Workflow Test ---")
    
    # 1. Create a job
    job_id = await queue.create_scrape_job("meta_ad_library", "test")
    print(f"1. Created job: {job_id[:8]}...")
    
    # 2. Store an asset
    await storage.store_asset("orch-test-001", {
        "source": "orchestrator_test",
        "title": "Orchestrator Test Asset"
    })
    print("2. Stored asset")
    
    # 3. Generate a prompt
    result = await llm.generate_prompt({"layout_type": "hero"}, "ecommerce")
    print(f"3. Generated prompt: {result.positive[:40]}...")
    
    # 4. Log to monitoring
    await monitoring.log("INFO", "Orchestrator test complete")
    print("4. Logged event")
    
    # Cleanup
    await storage.delete_asset("orch-test-001")
    await orch.shutdown()
    print("✅ Orchestrator shutdown")
    
    print()
    print("🎉 ALL ORCHESTRATOR TESTS PASSED!")

asyncio.run(test_orchestrator())
EOF
```

---

## 8. Testing the Agent Brain

### 8.1 Pipeline Status and Metrics

```bash
./venv/bin/python << 'EOF'
import asyncio
from agent.config import Config
from agent.orchestrator import Orchestrator

async def test_agent_brain():
    print("=" * 60)
    print("AGENT BRAIN TEST")
    print("=" * 60)
    
    # Initialize via orchestrator
    config = Config.from_environment()
    orch = Orchestrator(config)
    await orch.initialize()
    
    # Get agent brain
    agent = orch.get_agent()
    print(f"✅ AgentBrain initialized")
    
    # Get pipeline status
    status = await agent.get_pipeline_status()
    print(f"✅ Pipeline status:")
    print(f"   Running:      {status['running']}")
    print(f"   Active tasks: {status['active_tasks']}")
    print(f"   Metrics:      {status['metrics']}")
    
    # Check metrics structure
    print(f"\n✅ Agent metrics:")
    print(f"   Assets scraped:     {agent._metrics.assets_scraped}")
    print(f"   Features extracted: {agent._metrics.features_extracted}")
    print(f"   Prompts generated:  {agent._metrics.prompts_generated}")
    print(f"   Errors:             {agent._metrics.errors}")
    
    # Cleanup
    await orch.shutdown()
    print("✅ Agent shutdown")
    
    print()
    print("🎉 ALL AGENT BRAIN TESTS PASSED!")

asyncio.run(test_agent_brain())
EOF
```

---

## 9. Testing the Agent API

### 9.1 Start the API Server

**Open a new terminal (Terminal 1):**

```bash
cd /Users/monterey/Workspace/Projs/Tasmem/tasmem-scraping/creative-ads-platform
MODE=local ./venv/bin/uvicorn agent.api:app --host 0.0.0.0 --port 8081
```

Wait for: `INFO: Application startup complete.`

### 9.2 Test All Endpoints

**In another terminal (Terminal 2):**

```bash
cd /Users/monterey/Workspace/Projs/Tasmem/tasmem-scraping/creative-ads-platform

echo "=" 
echo "AGENT API ENDPOINT TESTS"
echo "="

echo -e "\n--- 1. Health Check ---"
curl -s http://localhost:8081/health | python3 -m json.tool

echo -e "\n--- 2. Readiness Check ---"
curl -s http://localhost:8081/ready | python3 -m json.tool

echo -e "\n--- 3. List Sources ---"
curl -s http://localhost:8081/sources | python3 -m json.tool

echo -e "\n--- 4. List Industries ---"
curl -s http://localhost:8081/industries | python3 -m json.tool

echo -e "\n--- 5. Create Scraping Job ---"
curl -s -X POST http://localhost:8081/scrape \
  -H "Content-Type: application/json" \
  -d '{"source": "meta_ad_library", "query": "technology", "max_items": 10}' | python3 -m json.tool

echo -e "\n--- 6. Queue Size ---"
curl -s http://localhost:8081/queue/size | python3 -m json.tool

echo -e "\n--- 7. Queue Metrics ---"
curl -s http://localhost:8081/queue/metrics | python3 -m json.tool

echo -e "\n--- 8. Pipeline Status ---"
curl -s http://localhost:8081/status | python3 -m json.tool

echo -e "\n--- 9. Pipeline Metrics ---"
curl -s http://localhost:8081/metrics | python3 -m json.tool

echo -e "\n🎉 ALL API ENDPOINT TESTS COMPLETE!"
```

### 9.3 Visit Swagger Documentation

Open in browser: **http://localhost:8081/docs**

You should see:
- Interactive API documentation
- All endpoints listed with descriptions
- Try-it-out functionality

---

## 10. Testing the Dashboard Backend

### 10.1 Start the Dashboard Backend

**In Terminal 3:**

```bash
cd /Users/monterey/Workspace/Projs/Tasmem/tasmem-scraping/creative-ads-platform/dashboard/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 10.2 Test Dashboard Backend Endpoints

**In Terminal 2:**

```bash
echo "="
echo "DASHBOARD BACKEND ENDPOINT TESTS"
echo "="

echo -e "\n--- 1. Root Endpoint ---"
curl -s http://localhost:8000/ | python3 -m json.tool

echo -e "\n--- 2. Health Check ---"
curl -s http://localhost:8000/health | python3 -m json.tool

echo -e "\n--- 3. Prometheus Metrics ---"
curl -s http://localhost:8000/metrics | head -20

echo -e "\n🎉 DASHBOARD BACKEND TESTS COMPLETE!"
```

### 10.3 Visit Dashboard Backend Swagger

Open in browser: **http://localhost:8000/docs**

---

## 11. Testing the Dashboard Frontend

### 11.1 Start the Frontend

**In Terminal 4:**

```bash
cd /Users/monterey/Workspace/Projs/Tasmem/tasmem-scraping/creative-ads-platform/dashboard/frontend
npm run dev
```

### 11.2 Access the Dashboard

Open in browser: **http://localhost:5173**

### 11.3 Manual UI Tests

| Test | Action | Expected Result |
|------|--------|-----------------|
| Page Load | Open http://localhost:5173 | Dashboard loads without errors |
| Navigation | Click sidebar menu items | Pages switch smoothly |
| Assets Page | Navigate to Assets | Shows asset list (may be empty) |
| Jobs Page | Navigate to Jobs | Shows job queue status |
| Settings Page | Navigate to Settings | Shows configuration options |

---

## 12. End-to-End Integration Test

### 12.1 Full Stack Test

With all services running (Agent API, Dashboard Backend, Dashboard Frontend):

```bash
./venv/bin/python << 'EOF'
import asyncio
import httpx

async def e2e_test():
    print("=" * 60)
    print("END-TO-END INTEGRATION TEST")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # Test 1: Agent API Health
        print("\n1. Testing Agent API...")
        resp = await client.get("http://localhost:8081/health")
        assert resp.status_code == 200, f"Agent health failed: {resp.status_code}"
        print(f"   ✅ Agent API healthy")
        
        # Test 2: Dashboard Backend Health
        print("\n2. Testing Dashboard Backend...")
        resp = await client.get("http://localhost:8000/health")
        assert resp.status_code == 200, f"Dashboard health failed: {resp.status_code}"
        print(f"   ✅ Dashboard Backend healthy")
        
        # Test 3: Create a job via Agent API
        print("\n3. Creating scraping job...")
        resp = await client.post(
            "http://localhost:8081/scrape",
            json={"source": "meta_ad_library", "query": "e2e_test", "max_items": 5}
        )
        assert resp.status_code == 200, f"Job creation failed: {resp.status_code}"
        job_data = resp.json()
        print(f"   ✅ Job created: {job_data['job_id'][:8]}...")
        
        # Test 4: Check queue size
        print("\n4. Checking queue...")
        resp = await client.get("http://localhost:8081/queue/size")
        assert resp.status_code == 200
        queue_size = resp.json()["size"]
        print(f"   ✅ Queue size: {queue_size}")
        
        # Test 5: Get metrics
        print("\n5. Getting metrics...")
        resp = await client.get("http://localhost:8081/metrics")
        assert resp.status_code == 200
        metrics = resp.json()
        print(f"   ✅ Metrics retrieved")
        
    print()
    print("=" * 60)
    print("🎉 END-TO-END TEST PASSED!")
    print("=" * 60)

asyncio.run(e2e_test())
EOF
```

---

## 📊 Test Results Summary

After completing all tests, fill in this checklist:

| Component | Status | Notes |
|-----------|--------|-------|
| Configuration | ☐ | |
| Local Storage | ☐ | |
| Local Queue | ☐ | |
| Local LLM | ☐ | |
| Local Monitoring | ☐ | |
| Orchestrator | ☐ | |
| Agent Brain | ☐ | |
| Agent API | ☐ | |
| Dashboard Backend | ☐ | |
| Dashboard Frontend | ☐ | |
| E2E Integration | ☐ | |

---

## 🔧 Quick Reference: All Services

| Service | Start Command | URL |
|---------|---------------|-----|
| Agent API | `MODE=local ./venv/bin/uvicorn agent.api:app --port 8081` | http://localhost:8081 |
| Dashboard Backend | `cd dashboard/backend && uvicorn app.main:app --port 8000` | http://localhost:8000 |
| Dashboard Frontend | `cd dashboard/frontend && npm run dev` | http://localhost:5173 |

---

## 🛑 Stopping All Services

```bash
# Kill all uvicorn processes
pkill -f uvicorn

# Kill frontend dev server
pkill -f "npm run dev"

# Or use Ctrl+C in each terminal
```

