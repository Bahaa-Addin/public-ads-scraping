"""
Step Definitions for Jobs Feature.

Tests job lifecycle management including:
- Job creation (scrape, pipeline)
- Job status transitions
- Job queries and filtering
- Error handling
"""

import json
import time
import asyncio
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from pytest_bdd import scenarios, given, when, then, parsers
import pytest

# Import common step definitions
from .common_steps import *

# Load scenarios from feature file
scenarios("../features/jobs.feature")


# ============================================
# Given Steps
# ============================================

@given(parsers.parse("{count:d} completed jobs exist in the database"))
def create_completed_jobs(context, count: int, data_manager, jobs_file, job_factory):
    """Create N completed jobs in the database."""
    data_manager.backup_file(jobs_file)
    jobs = []
    for i in range(count):
        job = job_factory(
            job_id=f"test-list-job-{i}",
            status="completed",
            created_at=(datetime.utcnow() - timedelta(hours=i)).isoformat(),
            completed_at=datetime.utcnow().isoformat()
        )
        jobs.append(job)
    data_manager.write_json(jobs_file, jobs)
    context.custom["created_jobs"] = jobs


@given(parsers.parse('a job with id "{job_id}" exists with status "{status}"'))
def create_job_with_id_and_status(context, job_id: str, status: str, data_manager, jobs_file, job_factory):
    """Create a specific job with given ID and status."""
    data_manager.backup_file(jobs_file)
    
    # Read existing jobs or start fresh
    existing = data_manager.read_json(jobs_file) or []
    
    job = job_factory(job_id=job_id, status=status)
    existing.append(job)
    data_manager.write_json(jobs_file, existing)
    context.custom["target_job"] = job


@given("jobs exist with various statuses")
def create_jobs_with_various_statuses(context, data_manager, jobs_file, job_factory):
    """Create jobs with different statuses for stats testing."""
    data_manager.backup_file(jobs_file)
    jobs = [
        job_factory(job_id="stats-pending-1", status="pending"),
        job_factory(job_id="stats-pending-2", status="pending"),
        job_factory(job_id="stats-in-progress-1", status="in_progress"),
        job_factory(job_id="stats-completed-1", status="completed"),
        job_factory(job_id="stats-completed-2", status="completed"),
        job_factory(job_id="stats-completed-3", status="completed"),
        job_factory(job_id="stats-failed-1", status="failed"),
    ]
    data_manager.write_json(jobs_file, jobs)


# ============================================
# When Steps
# ============================================

@when("I create 3 jobs simultaneously")
def create_concurrent_jobs(context, sync_dashboard_client):
    """Create multiple jobs concurrently."""
    import concurrent.futures
    
    def create_job(i):
        payload = {
            "sources": ["meta_ad_library"],
            "query": f"concurrent-test-{i}",
            "limit": 3
        }
        return sync_dashboard_client.post("/api/v1/jobs/scrape", json=payload)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(create_job, i) for i in range(3)]
        responses = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    context.custom["concurrent_responses"] = responses
    context.job_ids = [r.json().get("job_id") for r in responses if r.status_code == 200]


@when("I create and monitor a job")
def create_and_monitor_job(context, sync_dashboard_client):
    """Create a job and track its status transitions."""
    payload = {"sources": ["meta_ad_library"], "query": "monitor", "limit": 3}
    response = sync_dashboard_client.post("/api/v1/jobs/scrape", json=payload)
    context.response = response
    context.response_data = response.json()
    context.job_id = context.response_data.get("job_id")
    context.custom["status_history"] = ["pending"]  # Initial status


# ============================================
# Then Steps
# ============================================

@then(parsers.parse("the response should contain exactly {count:d} jobs"))
def assert_job_count(context, count: int):
    """Assert response contains exact number of jobs."""
    jobs = context.response_data.get("jobs", context.response_data)
    if isinstance(jobs, dict):
        jobs = jobs.get("items", [])
    assert len(jobs) == count, f"Expected {count} jobs, got {len(jobs)}"


@then(parsers.parse('the response should have "total" greater than or equal to {value:d}'))
def assert_total_gte(context, value: int):
    """Assert total is at least the given value."""
    total = context.response_data.get("total", 0)
    assert total >= value, f"Expected total >= {value}, got {total}"


@then(parsers.parse('the response should contain job details with id "{job_id}"'))
def assert_job_details(context, job_id: str):
    """Assert response contains job with the given ID."""
    job = context.response_data
    assert job.get("id") == job_id, f"Expected job id '{job_id}', got '{job.get('id')}'"


@then("the response should contain status counts")
def assert_status_counts(context):
    """Assert response contains job status counts."""
    data = context.response_data
    # The response might be in different formats
    if isinstance(data, list):
        assert len(data) > 0, "Expected status counts array to be non-empty"
    elif isinstance(data, dict):
        # Check for expected keys
        assert any(k in data for k in ["pending", "in_progress", "completed", "failed", "counts"]), \
            f"Expected status counts in response: {data}"


@then("all 3 jobs should be created with unique IDs")
def assert_unique_job_ids(context):
    """Assert all concurrent jobs have unique IDs."""
    job_ids = context.job_ids
    assert len(job_ids) == 3, f"Expected 3 job IDs, got {len(job_ids)}"
    assert len(set(job_ids)) == 3, f"Job IDs are not unique: {job_ids}"


@then("all jobs should have valid status")
def assert_all_valid_status(context, sync_dashboard_client):
    """Assert all created jobs have valid status."""
    valid_statuses = ["pending", "in_progress", "completed", "failed"]
    for job_id in context.job_ids:
        response = sync_dashboard_client.get(f"/api/v1/jobs/{job_id}")
        if response.status_code == 200:
            job = response.json()
            assert job.get("status") in valid_statuses, \
                f"Job {job_id} has invalid status: {job.get('status')}"


@then("the job status should only transition through valid states")
def assert_valid_state_transitions(context, sync_dashboard_client):
    """Verify job follows valid state machine transitions."""
    valid_transitions = {
        "pending": ["in_progress", "failed"],
        "in_progress": ["completed", "failed"],
        "completed": [],  # Terminal state
        "failed": []  # Terminal state
    }
    
    job_id = context.job_id
    last_status = "pending"
    
    # Poll for a few seconds to catch transitions
    for _ in range(30):
        response = sync_dashboard_client.get(f"/api/v1/jobs/{job_id}")
        if response.status_code == 200:
            current_status = response.json().get("status")
            if current_status != last_status:
                # Verify transition is valid
                assert current_status in valid_transitions.get(last_status, []) or current_status == last_status, \
                    f"Invalid transition from {last_status} to {current_status}"
                last_status = current_status
                
                # Stop if we reach a terminal state
                if current_status in ["completed", "failed"]:
                    break
        time.sleep(1)
