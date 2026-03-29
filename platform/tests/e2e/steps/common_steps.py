"""
Common Step Definitions shared across all features.

These steps handle:
- Service health checks
- HTTP request/response handling
- Data file management
- Common assertions
"""

import json
import asyncio
import httpx
from datetime import datetime
from pathlib import Path
from pytest_bdd import given, when, then, parsers
from typing import List

# Import fixtures from conftest
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================
# Service Health Check Steps
# ============================================

@given("the dashboard backend is running on port 8000")
def dashboard_running(context, sync_dashboard_client):
    """Verify dashboard backend is running."""
    try:
        response = sync_dashboard_client.get("/api/v1/health")
        assert response.status_code == 200, f"Dashboard health check failed: {response.status_code}"
        context.dashboard_client = sync_dashboard_client
    except httpx.ConnectError as e:
        raise AssertionError(f"Dashboard backend is not running on port 8000: {e}")


@given("the agent API is running on port 8081")
def agent_running(context):
    """Verify agent API is running."""
    try:
        with httpx.Client(base_url="http://localhost:8081", timeout=10.0) as client:
            response = client.get("/health")
            assert response.status_code == 200, f"Agent health check failed: {response.status_code}"
    except httpx.ConnectError as e:
        raise AssertionError(f"Agent API is not running on port 8081: {e}")


@given("the scraper service is running on port 3001")
def scraper_running(context):
    """Verify scraper service is running."""
    try:
        with httpx.Client(base_url="http://localhost:3001", timeout=10.0) as client:
            response = client.get("/health")
            assert response.status_code == 200, f"Scraper health check failed: {response.status_code}"
    except httpx.ConnectError:
        # Scraper might not be required for all tests
        context.custom["scraper_available"] = False


@given("the scraper service is not responding")
def scraper_not_responding(context):
    """Mark that scraper is expected to be unavailable."""
    context.custom["scraper_available"] = False


@given("the scraper service on port 3001 is not running")
def scraper_not_running(context):
    """Mark scraper as unavailable."""
    context.custom["scraper_available"] = False


# ============================================
# Data File Management Steps
# ============================================

@given("the data files are reset to clean state")
def reset_data_files(context, clean_data_files):
    """Reset all data files to empty state."""
    context.custom["data_manager"] = clean_data_files


@given("metrics files are initialized")
def metrics_files_initialized(context, data_manager, time_series_file):
    """Ensure metrics files exist with valid structure."""
    if not time_series_file.exists():
        data_manager.write_json(time_series_file, {})


# ============================================
# HTTP Request Steps
# ============================================

@when(parsers.parse('I GET "{endpoint}"'))
def get_request(context, endpoint, sync_dashboard_client):
    """Make a GET request to the dashboard backend."""
    context.response = sync_dashboard_client.get(endpoint)
    try:
        context.response_data = context.response.json()
    except json.JSONDecodeError:
        context.response_data = None


@when(parsers.parse('I POST to "{endpoint}" with payload:'))
def post_request_with_payload(context, endpoint, sync_dashboard_client):
    """Make a POST request with JSON payload from docstring."""
    # The payload is passed as the step's docstring
    # pytest-bdd passes it as a text block
    payload = json.loads(context.text) if hasattr(context, 'text') else {}
    context.response = sync_dashboard_client.post(endpoint, json=payload)
    try:
        context.response_data = context.response.json()
    except json.JSONDecodeError:
        context.response_data = None
    
    # Store job_id if present
    if context.response_data and "job_id" in context.response_data:
        context.job_id = context.response_data["job_id"]
        context.job_ids.append(context.job_id)


# ============================================
# Response Status Assertions
# ============================================

@then(parsers.parse("the response status should be {status:d}"))
def assert_response_status(context, status: int):
    """Assert exact response status code."""
    assert context.response.status_code == status, \
        f"Expected status {status}, got {context.response.status_code}: {context.response.text}"


@then(parsers.parse("the response status should be one of [{statuses}]"))
def assert_response_status_in(context, statuses: str):
    """Assert response status is one of the given values."""
    status_list = [int(s.strip()) for s in statuses.split(",")]
    assert context.response.status_code in status_list, \
        f"Expected status in {status_list}, got {context.response.status_code}: {context.response.text}"


# ============================================
# Response Structure Assertions
# ============================================

@then(parsers.parse('the response should contain a "{field}" field'))
def assert_response_has_field(context, field: str):
    """Assert response JSON contains the given field."""
    assert context.response_data is not None, "Response is not valid JSON"
    assert field in context.response_data, \
        f"Response missing field '{field}': {context.response_data}"


@then("the response should be an array")
def assert_response_is_array(context):
    """Assert response is a JSON array."""
    assert isinstance(context.response_data, list), \
        f"Expected array, got {type(context.response_data)}"


@then(parsers.parse('the response should have field "{field}" of type "{field_type}"'))
def assert_field_type(context, field: str, field_type: str):
    """Assert response field exists and has correct type."""
    assert context.response_data is not None, "Response is not valid JSON"
    assert field in context.response_data, f"Missing field: {field}"
    
    value = context.response_data[field]
    type_map = {
        "string": str,
        "number": (int, float),
        "array": list,
        "boolean": bool,
        "object": dict
    }
    expected_type = type_map.get(field_type)
    assert isinstance(value, expected_type), \
        f"Field '{field}' should be {field_type}, got {type(value)}"


@then(parsers.parse('the response should have numeric field "{field}"'))
def assert_numeric_field(context, field: str):
    """Assert response has a numeric field."""
    assert context.response_data is not None, "Response is not valid JSON"
    assert field in context.response_data, f"Missing field: {field}"
    value = context.response_data[field]
    assert isinstance(value, (int, float)), \
        f"Field '{field}' should be numeric, got {type(value)}"


@then("the data array should be empty")
def assert_data_array_empty(context):
    """Assert the 'data' field is an empty array."""
    assert context.response_data is not None, "Response is not valid JSON"
    data = context.response_data.get("data", context.response_data)
    if isinstance(data, list):
        assert len(data) == 0, f"Expected empty array, got {len(data)} items"
    elif isinstance(data, dict) and "data" in data:
        assert len(data["data"]) == 0, f"Expected empty array, got {len(data['data'])} items"


@then("no server error should occur")
def assert_no_server_error(context):
    """Assert response is not a 5xx error."""
    assert context.response.status_code < 500, \
        f"Server error occurred: {context.response.status_code} - {context.response.text}"


@then("no server crash should occur")
def assert_no_crash(context):
    """Assert server is still responding."""
    assert context.response.status_code < 500, \
        f"Server error: {context.response.status_code}"


# ============================================
# Timing Steps
# ============================================

@then(parsers.parse('within {seconds:d} seconds the job status should be "{expected_status}"'))
def wait_for_job_status(context, seconds: int, expected_status: str, sync_dashboard_client):
    """Poll until job reaches expected status or timeout."""
    import time
    start = time.time()
    job_id = context.job_id
    
    while time.time() - start < seconds:
        response = sync_dashboard_client.get(f"/api/v1/jobs/{job_id}")
        if response.status_code == 200:
            job = response.json()
            if job.get("status") == expected_status:
                context.response_data = job
                return
        time.sleep(1)
    
    raise AssertionError(f"Job {job_id} did not reach status '{expected_status}' within {seconds}s")


@then(parsers.parse('within {seconds:d} seconds the job status should be one of [{statuses}]'))
def wait_for_job_status_in(context, seconds: int, statuses: str, sync_dashboard_client):
    """Poll until job reaches one of the expected statuses."""
    import time
    status_list = [s.strip().strip('"') for s in statuses.split(",")]
    start = time.time()
    job_id = context.job_id
    
    while time.time() - start < seconds:
        response = sync_dashboard_client.get(f"/api/v1/jobs/{job_id}")
        if response.status_code == 200:
            job = response.json()
            if job.get("status") in status_list:
                context.response_data = job
                return
        time.sleep(1)
    
    raise AssertionError(f"Job {job_id} did not reach status in {status_list} within {seconds}s")


# ============================================
# Timestamp Assertions
# ============================================

@then(parsers.parse('the job should have a "{field}" timestamp'))
def assert_job_has_timestamp(context, field: str, sync_dashboard_client):
    """Assert job has a timestamp field."""
    job_id = context.job_id
    response = sync_dashboard_client.get(f"/api/v1/jobs/{job_id}")
    job = response.json()
    assert field in job and job[field] is not None, \
        f"Job missing timestamp field '{field}'"
    # Validate ISO format
    try:
        datetime.fromisoformat(job[field].replace('Z', '+00:00'))
    except ValueError:
        raise AssertionError(f"Invalid timestamp format for '{field}': {job[field]}")


@then(parsers.parse('"{field1}" should be after "{field2}"'))
def assert_timestamp_order(context, field1: str, field2: str, sync_dashboard_client):
    """Assert one timestamp is after another."""
    job_id = context.job_id
    response = sync_dashboard_client.get(f"/api/v1/jobs/{job_id}")
    job = response.json()
    
    ts1 = datetime.fromisoformat(job[field1].replace('Z', '+00:00'))
    ts2 = datetime.fromisoformat(job[field2].replace('Z', '+00:00'))
    assert ts1 >= ts2, f"{field1} ({ts1}) should be after {field2} ({ts2})"


@then("the job should have timestamps in ISO 8601 format")
def assert_iso_timestamps(context, sync_dashboard_client):
    """Verify all job timestamps are ISO 8601 format."""
    job_id = context.job_id
    response = sync_dashboard_client.get(f"/api/v1/jobs/{job_id}")
    job = response.json()
    
    timestamp_fields = ["created_at", "started_at", "completed_at"]
    for field in timestamp_fields:
        if job.get(field):
            try:
                datetime.fromisoformat(job[field].replace('Z', '+00:00'))
            except ValueError:
                raise AssertionError(f"Invalid ISO 8601 format for {field}: {job[field]}")
