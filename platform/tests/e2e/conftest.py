"""
E2E Test Configuration and Fixtures

Provides shared fixtures for all E2E tests including:
- API clients (dashboard backend, agent, scraper)
- Data file management
- Service health checks
- Test data setup/teardown
"""

import os
import sys
import json
import asyncio
import pytest
import httpx
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

# Note: Common steps are imported directly in each test file

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ============================================
# Configuration
# ============================================

DASHBOARD_BACKEND_URL = os.getenv("DASHBOARD_BACKEND_URL", "http://localhost:8000")
AGENT_API_URL = os.getenv("AGENT_API_URL", "http://localhost:8081")
SCRAPER_API_URL = os.getenv("SCRAPER_API_URL", "http://localhost:3001")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

DATA_DIR = PROJECT_ROOT / "data"
JOBS_FILE = DATA_DIR / "db" / "jobs.json"
ASSETS_FILE = DATA_DIR / "db" / "assets.json"
SCRAPER_STATUS_FILE = DATA_DIR / "metrics" / "scraper_status.json"
TIME_SERIES_FILE = DATA_DIR / "metrics" / "time_series.json"
SYSTEM_METRICS_FILE = DATA_DIR / "metrics" / "system_metrics.json"
PIPELINE_LOG_FILE = DATA_DIR / "logs" / "pipeline.log"


# ============================================
# Pytest Configuration
# ============================================

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "happy_path: mark test as happy path scenario")
    config.addinivalue_line("markers", "negative: mark test as negative scenario")
    config.addinivalue_line("markers", "edge_case: mark test as edge case scenario")
    config.addinivalue_line("markers", "critical: mark test as critical (must pass)")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_scraper: test requires scraper service")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================
# Service URL Fixtures
# ============================================

@pytest.fixture(scope="session")
def dashboard_url() -> str:
    """Dashboard backend API URL."""
    return DASHBOARD_BACKEND_URL


@pytest.fixture(scope="session")
def agent_url() -> str:
    """Agent API URL."""
    return AGENT_API_URL


@pytest.fixture(scope="session")
def scraper_url() -> str:
    """Scraper service URL."""
    return SCRAPER_API_URL


@pytest.fixture(scope="session")
def frontend_url() -> str:
    """Frontend application URL."""
    return FRONTEND_URL


# ============================================
# HTTP Client Fixtures
# ============================================

@pytest.fixture(scope="session")
async def dashboard_client() -> httpx.AsyncClient:
    """Async HTTP client for dashboard backend."""
    async with httpx.AsyncClient(
        base_url=DASHBOARD_BACKEND_URL,
        timeout=30.0,
        headers={"Content-Type": "application/json"}
    ) as client:
        yield client


@pytest.fixture(scope="session")
async def agent_client() -> httpx.AsyncClient:
    """Async HTTP client for agent API."""
    async with httpx.AsyncClient(
        base_url=AGENT_API_URL,
        timeout=30.0,
        headers={"Content-Type": "application/json"}
    ) as client:
        yield client


@pytest.fixture(scope="session")
async def scraper_client() -> httpx.AsyncClient:
    """Async HTTP client for scraper service."""
    async with httpx.AsyncClient(
        base_url=SCRAPER_API_URL,
        timeout=30.0,
        headers={"Content-Type": "application/json"}
    ) as client:
        yield client


@pytest.fixture
def sync_dashboard_client() -> httpx.Client:
    """Sync HTTP client for dashboard backend (for step definitions)."""
    with httpx.Client(
        base_url=DASHBOARD_BACKEND_URL,
        timeout=30.0,
        headers={"Content-Type": "application/json"}
    ) as client:
        yield client


# ============================================
# Service Health Check Fixtures
# ============================================

@pytest.fixture(scope="session")
async def dashboard_running(dashboard_client: httpx.AsyncClient) -> bool:
    """Check if dashboard backend is running."""
    try:
        response = await dashboard_client.get("/api/v1/health")
        return response.status_code == 200
    except httpx.ConnectError:
        return False


@pytest.fixture(scope="session")
async def agent_running(agent_client: httpx.AsyncClient) -> bool:
    """Check if agent API is running."""
    try:
        response = await agent_client.get("/health")
        return response.status_code == 200
    except httpx.ConnectError:
        return False


@pytest.fixture(scope="session")
async def scraper_running(scraper_client: httpx.AsyncClient) -> bool:
    """Check if scraper service is running."""
    try:
        response = await scraper_client.get("/health")
        return response.status_code == 200
    except httpx.ConnectError:
        return False


@pytest.fixture
def require_all_services(dashboard_running, agent_running, scraper_running):
    """Skip test if any service is not running."""
    if not dashboard_running:
        pytest.skip("Dashboard backend is not running")
    if not agent_running:
        pytest.skip("Agent API is not running")
    if not scraper_running:
        pytest.skip("Scraper service is not running")


# ============================================
# Data File Fixtures
# ============================================

@pytest.fixture
def data_dir() -> Path:
    """Data directory path."""
    return DATA_DIR


@pytest.fixture
def jobs_file() -> Path:
    """Jobs data file path."""
    return JOBS_FILE


@pytest.fixture
def assets_file() -> Path:
    """Assets data file path."""
    return ASSETS_FILE


@pytest.fixture
def scraper_status_file() -> Path:
    """Scraper status file path."""
    return SCRAPER_STATUS_FILE


@pytest.fixture
def time_series_file() -> Path:
    """Time series metrics file path."""
    return TIME_SERIES_FILE


@pytest.fixture
def pipeline_log_file() -> Path:
    """Pipeline log file path."""
    return PIPELINE_LOG_FILE


class DataFileManager:
    """Manages reading and writing test data files."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._backups: Dict[Path, Any] = {}
    
    def backup_file(self, file_path: Path) -> None:
        """Backup a file's contents."""
        if file_path.exists():
            with open(file_path, 'r') as f:
                content = f.read()
                try:
                    self._backups[file_path] = json.loads(content) if content.strip() else None
                except json.JSONDecodeError:
                    self._backups[file_path] = content
        else:
            self._backups[file_path] = None
    
    def restore_file(self, file_path: Path) -> None:
        """Restore a file from backup."""
        if file_path in self._backups:
            content = self._backups[file_path]
            if content is None:
                if file_path.exists():
                    file_path.unlink()
            elif isinstance(content, str):
                with open(file_path, 'w') as f:
                    f.write(content)
            else:
                with open(file_path, 'w') as f:
                    json.dump(content, f, indent=2)
    
    def restore_all(self) -> None:
        """Restore all backed up files."""
        for file_path in self._backups:
            self.restore_file(file_path)
        self._backups.clear()
    
    def read_json(self, file_path: Path) -> Any:
        """Read JSON data from file."""
        if not file_path.exists():
            return None
        with open(file_path, 'r') as f:
            content = f.read()
            if not content.strip():
                return None
            return json.loads(content)
    
    def write_json(self, file_path: Path, data: Any) -> None:
        """Write JSON data to file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def clear_file(self, file_path: Path, empty_value: Any = None) -> None:
        """Clear a file to empty state."""
        if empty_value is not None:
            self.write_json(file_path, empty_value)
        elif file_path.suffix == '.log':
            with open(file_path, 'w') as f:
                f.write("")
        else:
            self.write_json(file_path, [])


@pytest.fixture
def data_manager() -> DataFileManager:
    """Data file manager instance."""
    manager = DataFileManager(DATA_DIR)
    yield manager
    manager.restore_all()


@pytest.fixture
def clean_data_files(data_manager: DataFileManager):
    """Reset all data files to clean state."""
    # Backup existing files
    data_manager.backup_file(JOBS_FILE)
    data_manager.backup_file(ASSETS_FILE)
    data_manager.backup_file(SCRAPER_STATUS_FILE)
    data_manager.backup_file(TIME_SERIES_FILE)
    data_manager.backup_file(SYSTEM_METRICS_FILE)
    data_manager.backup_file(PIPELINE_LOG_FILE)
    
    # Clear to empty state
    data_manager.clear_file(JOBS_FILE, [])
    data_manager.clear_file(ASSETS_FILE, [])
    data_manager.clear_file(SCRAPER_STATUS_FILE, [])
    data_manager.clear_file(TIME_SERIES_FILE, {})
    data_manager.clear_file(SYSTEM_METRICS_FILE, {})
    data_manager.clear_file(PIPELINE_LOG_FILE)
    
    yield data_manager
    
    # Restore happens automatically via data_manager fixture


# ============================================
# Test Data Factories
# ============================================

@pytest.fixture
def job_factory():
    """Factory for creating test job data."""
    def _create_job(
        job_id: str = None,
        job_type: str = "scrape",
        status: str = "pending",
        sources: List[str] = None,
        assets_processed: int = 0,
        error_message: str = None,
        created_at: str = None,
        started_at: str = None,
        completed_at: str = None
    ) -> Dict[str, Any]:
        now = datetime.utcnow()
        return {
            "id": job_id or f"test-job-{now.timestamp()}",
            "job_type": job_type,
            "status": status,
            "payload": {
                "sources": sources or ["meta_ad_library"],
                "query": "test",
                "limit": 10
            },
            "assets_processed": assets_processed,
            "retry_count": 0,
            "error_message": error_message,
            "created_at": created_at or now.isoformat(),
            "started_at": started_at,
            "completed_at": completed_at
        }
    return _create_job


@pytest.fixture
def asset_factory():
    """Factory for creating test asset data."""
    def _create_asset(
        asset_id: str = None,
        source: str = "meta_ad_library",
        title: str = "Test Ad",
        industry: str = "technology",
        image_url: str = None
    ) -> Dict[str, Any]:
        now = datetime.utcnow()
        return {
            "id": asset_id or f"test-asset-{now.timestamp()}",
            "source": source,
            "source_url": f"https://example.com/ad/{asset_id or 'test'}",
            "image_url": image_url or "https://example.com/image.jpg",
            "asset_type": "image",
            "title": title,
            "advertiser_name": "Test Advertiser",
            "industry": industry,
            "created_at": now.isoformat()
        }
    return _create_asset


@pytest.fixture
def log_entry_factory():
    """Factory for creating test log entries."""
    def _create_log(
        level: str = "info",
        message: str = "Test log message",
        source: str = "agent",
        job_id: str = None
    ) -> Dict[str, Any]:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "source": source,
            "job_id": job_id,
            "asset_id": None,
            "metadata": None
        }
    return _create_log


@pytest.fixture
def scraper_status_factory():
    """Factory for creating test scraper status data."""
    def _create_status(
        source: str = "meta_ad_library",
        enabled: bool = True,
        running: bool = False,
        items_scraped: int = 0,
        success_rate: float = 0,
        error_count: int = 0,
        last_run: str = None
    ) -> Dict[str, Any]:
        return {
            "source": source,
            "enabled": enabled,
            "running": running,
            "items_scraped": items_scraped,
            "success_rate": success_rate,
            "error_count": error_count,
            "last_run": last_run
        }
    return _create_status


# ============================================
# Async Utilities
# ============================================

@pytest.fixture
def wait_for_condition():
    """Fixture for polling until a condition is met."""
    async def _wait(
        condition_fn,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
        description: str = "condition"
    ):
        start_time = asyncio.get_event_loop().time()
        while True:
            try:
                result = await condition_fn() if asyncio.iscoroutinefunction(condition_fn) else condition_fn()
                if result:
                    return result
            except Exception:
                pass
            
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise TimeoutError(f"Timed out waiting for {description} after {timeout}s")
            
            await asyncio.sleep(poll_interval)
    
    return _wait


@pytest.fixture
def wait_for_job_status(dashboard_client: httpx.AsyncClient, wait_for_condition):
    """Wait for a job to reach a specific status."""
    async def _wait(job_id: str, expected_status: str, timeout: float = 120.0):
        async def check_status():
            response = await dashboard_client.get(f"/api/v1/jobs/{job_id}")
            if response.status_code == 200:
                job = response.json()
                return job.get("status") == expected_status
            return False
        
        return await wait_for_condition(
            check_status,
            timeout=timeout,
            description=f"job {job_id} to be {expected_status}"
        )
    
    return _wait


# ============================================
# Response Validation Helpers
# ============================================

class ResponseValidator:
    """Helper for validating API responses."""
    
    @staticmethod
    def assert_status(response: httpx.Response, expected: int):
        """Assert response status code."""
        assert response.status_code == expected, \
            f"Expected status {expected}, got {response.status_code}: {response.text}"
    
    @staticmethod
    def assert_status_in(response: httpx.Response, expected: List[int]):
        """Assert response status code is in list."""
        assert response.status_code in expected, \
            f"Expected status in {expected}, got {response.status_code}: {response.text}"
    
    @staticmethod
    def assert_json_structure(data: dict, required_fields: List[str]):
        """Assert dict has required fields."""
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    @staticmethod
    def assert_valid_timestamp(timestamp: str):
        """Assert timestamp is valid ISO 8601 format."""
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pytest.fail(f"Invalid timestamp format: {timestamp}")
    
    @staticmethod
    def assert_in_range(value: float, min_val: float, max_val: float, field_name: str = "value"):
        """Assert value is within range."""
        assert min_val <= value <= max_val, \
            f"{field_name} {value} not in range [{min_val}, {max_val}]"


@pytest.fixture
def validator() -> ResponseValidator:
    """Response validator instance."""
    return ResponseValidator()


# ============================================
# Context Storage for Step Definitions
# ============================================

class TestContext:
    """Stores state between BDD steps."""
    
    def __init__(self):
        self.response: Optional[httpx.Response] = None
        self.response_data: Any = None
        self.job_id: Optional[str] = None
        self.job_ids: List[str] = []
        self.asset_ids: List[str] = []
        self.error: Optional[Exception] = None
        self.events: List[dict] = []
        self.start_time: Optional[datetime] = None
        self.custom: Dict[str, Any] = {}
    
    def reset(self):
        """Reset all context state."""
        self.__init__()


@pytest.fixture
def context() -> TestContext:
    """Fresh test context for each test."""
    return TestContext()
