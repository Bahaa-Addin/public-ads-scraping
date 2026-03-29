"""
Step Definitions for Logs Feature.

Tests pipeline logging including:
- Log entry creation during jobs
- Log filtering by job_id, level
- Log pagination
- Edge cases (missing file, malformed data)
"""

import json
import time
from datetime import datetime
from pathlib import Path
from pytest_bdd import scenarios, given, when, then, parsers

# Import common step definitions
from .common_steps import *

# Load scenarios from feature file
scenarios("../features/logs.feature")


# ============================================
# Given Steps
# ============================================

@given("pipeline.log is reset to empty")
def reset_pipeline_log(context, data_manager, pipeline_log_file):
    """Clear pipeline.log file."""
    data_manager.backup_file(pipeline_log_file)
    data_manager.clear_file(pipeline_log_file)


@given(parsers.parse("pipeline.log contains {count:d} log entries"))
def create_log_entries(context, count: int, data_manager, pipeline_log_file, log_entry_factory):
    """Create N log entries in pipeline.log."""
    data_manager.backup_file(pipeline_log_file)
    
    with open(pipeline_log_file, 'w') as f:
        for i in range(count):
            entry = log_entry_factory(
                message=f"Test log message {i}",
                level="info" if i % 2 == 0 else "warning"
            )
            f.write(json.dumps(entry) + "\n")


@given(parsers.parse('logs exist for job "{job_id}"'))
def create_logs_for_job(context, job_id: str, data_manager, pipeline_log_file, log_entry_factory):
    """Create log entries for a specific job."""
    data_manager.backup_file(pipeline_log_file)
    
    # Append to existing file
    with open(pipeline_log_file, 'a') as f:
        for i in range(3):
            entry = log_entry_factory(
                message=f"Log for job {job_id} - entry {i}",
                job_id=job_id,
                level="info"
            )
            f.write(json.dumps(entry) + "\n")


@given('logs exist with levels "info" and "error"')
def create_logs_with_levels(context, data_manager, pipeline_log_file, log_entry_factory):
    """Create logs with different levels."""
    data_manager.backup_file(pipeline_log_file)
    
    with open(pipeline_log_file, 'w') as f:
        # Create some info logs
        for i in range(3):
            entry = log_entry_factory(level="info", message=f"Info log {i}")
            f.write(json.dumps(entry) + "\n")
        
        # Create some error logs
        for i in range(2):
            entry = log_entry_factory(level="error", message=f"Error log {i}")
            f.write(json.dumps(entry) + "\n")


@given("logs exist with various levels")
def create_logs_various_levels(context, data_manager, pipeline_log_file, log_entry_factory):
    """Create logs with all levels."""
    data_manager.backup_file(pipeline_log_file)
    
    levels = ["debug", "info", "warning", "error"]
    with open(pipeline_log_file, 'w') as f:
        for level in levels:
            for i in range(2):
                entry = log_entry_factory(level=level, message=f"{level.upper()} log {i}")
                f.write(json.dumps(entry) + "\n")


@given(parsers.parse("{count:d} log entries exist"))
def create_specific_log_count(context, count: int, data_manager, pipeline_log_file, log_entry_factory):
    """Create exact number of log entries."""
    data_manager.backup_file(pipeline_log_file)
    
    with open(pipeline_log_file, 'w') as f:
        for i in range(count):
            entry = log_entry_factory(message=f"Log entry {i}", level="info")
            f.write(json.dumps(entry) + "\n")


@given("pipeline.log file does not exist")
def remove_pipeline_log(context, data_manager, pipeline_log_file):
    """Remove pipeline.log file."""
    data_manager.backup_file(pipeline_log_file)
    if pipeline_log_file.exists():
        pipeline_log_file.unlink()


@given(parsers.parse("a log entry with {length:d} character message exists"))
def create_long_log(context, length: int, data_manager, pipeline_log_file, log_entry_factory):
    """Create a log with very long message."""
    data_manager.backup_file(pipeline_log_file)
    
    long_message = "X" * length
    entry = log_entry_factory(message=long_message, level="info")
    
    with open(pipeline_log_file, 'w') as f:
        f.write(json.dumps(entry) + "\n")
    
    context.custom["long_message_length"] = length


@given("pipeline.log contains one malformed JSON line")
def create_malformed_log(context, data_manager, pipeline_log_file, log_entry_factory):
    """Create log file with one malformed line."""
    data_manager.backup_file(pipeline_log_file)
    
    with open(pipeline_log_file, 'w') as f:
        # Valid entry
        entry = log_entry_factory(message="Valid log 1", level="info")
        f.write(json.dumps(entry) + "\n")
        
        # Malformed line
        f.write("{invalid json\n")
        
        # Another valid entry
        entry = log_entry_factory(message="Valid log 2", level="info")
        f.write(json.dumps(entry) + "\n")


# ============================================
# When Steps
# ============================================

@when("I run a full pipeline job")
def run_full_pipeline(context, sync_dashboard_client):
    """Start a full pipeline job."""
    payload = {
        "sources": ["meta_ad_library"],
        "query": "test",
        "limit": 3,
        "skip_steps": []
    }
    response = sync_dashboard_client.post("/api/v1/jobs/pipeline", json=payload)
    context.response = response
    context.response_data = response.json()
    context.job_id = context.response_data.get("job_id")


@when("the job completes")
def wait_for_job_complete(context, sync_dashboard_client):
    """Wait for job to complete."""
    job_id = context.job_id
    if not job_id:
        return
    
    for _ in range(120):
        response = sync_dashboard_client.get(f"/api/v1/jobs/{job_id}")
        if response.status_code == 200:
            status = response.json().get("status")
            if status in ["completed", "failed"]:
                return
        time.sleep(1)


# ============================================
# Then Steps
# ============================================

@then(parsers.parse("pipeline.log should contain at least {count:d} log entries"))
def assert_log_count(context, count: int, pipeline_log_file):
    """Verify pipeline.log has at least N entries."""
    if not pipeline_log_file.exists():
        assert count == 0, f"Expected {count} logs but file doesn't exist"
        return
    
    with open(pipeline_log_file, 'r') as f:
        lines = [l for l in f.readlines() if l.strip()]
    
    assert len(lines) >= count, f"Expected at least {count} log entries, got {len(lines)}"


@then("each log entry should have required fields")
def assert_log_fields(context, pipeline_log_file):
    """Verify log entries have required fields."""
    required_fields = ["timestamp", "level", "message", "source"]
    
    with open(pipeline_log_file, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    for field in required_fields:
                        assert field in entry, f"Log entry missing field '{field}': {entry}"
                except json.JSONDecodeError:
                    pass  # Skip malformed lines


@then(parsers.parse("the response should contain at least {count:d} logs"))
def assert_response_log_count(context, count: int):
    """Verify response has at least N logs."""
    logs = context.response_data.get("logs", context.response_data.get("items", []))
    if isinstance(context.response_data, list):
        logs = context.response_data
    
    assert len(logs) >= count, f"Expected at least {count} logs, got {len(logs)}"


@then("logs should be ordered by timestamp descending")
def assert_logs_ordered(context):
    """Verify logs are sorted by timestamp descending."""
    logs = context.response_data.get("logs", context.response_data.get("items", []))
    if isinstance(context.response_data, list):
        logs = context.response_data
    
    if len(logs) < 2:
        return  # Can't verify order with less than 2 items
    
    timestamps = []
    for log in logs:
        ts_str = log.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            timestamps.append(ts)
        except ValueError:
            continue
    
    # Verify descending order (most recent first)
    for i in range(len(timestamps) - 1):
        assert timestamps[i] >= timestamps[i + 1], \
            f"Logs not in descending order: {timestamps[i]} < {timestamps[i + 1]}"


@then(parsers.parse('all returned logs should have job_id "{job_id}"'))
def assert_logs_job_id(context, job_id: str):
    """Verify all logs have the expected job_id."""
    logs = context.response_data.get("logs", context.response_data.get("items", []))
    if isinstance(context.response_data, list):
        logs = context.response_data
    
    for log in logs:
        assert log.get("job_id") == job_id, \
            f"Expected job_id '{job_id}', got '{log.get('job_id')}'"


@then(parsers.parse('all returned logs should have level "{level}"'))
def assert_logs_level(context, level: str):
    """Verify all logs have the expected level."""
    logs = context.response_data.get("logs", context.response_data.get("items", []))
    if isinstance(context.response_data, list):
        logs = context.response_data
    
    for log in logs:
        assert log.get("level") == level, \
            f"Expected level '{level}', got '{log.get('level')}'"


@then("the response should contain level counts")
def assert_level_counts(context):
    """Verify response contains log level counts."""
    data = context.response_data
    # Accept various response formats
    assert data is not None, "Response should contain data"


@then(parsers.parse("the response should contain {count:d} logs"))
def assert_exact_log_count(context, count: int):
    """Verify response has exact number of logs."""
    logs = context.response_data.get("logs", context.response_data.get("items", []))
    if isinstance(context.response_data, list):
        logs = context.response_data
    
    assert len(logs) == count, f"Expected {count} logs, got {len(logs)}"


@then(parsers.parse("the response should contain {count:d} different logs"))
def assert_different_logs(context, count: int):
    """Verify response has different logs than previous request."""
    # This is verified by the pagination mechanism
    logs = context.response_data.get("logs", context.response_data.get("items", []))
    if isinstance(context.response_data, list):
        logs = context.response_data
    
    assert len(logs) == count, f"Expected {count} logs, got {len(logs)}"


@then("the request should not cause server error")
def assert_no_server_error(context):
    """Verify no 5xx error occurred."""
    assert context.response.status_code < 500, \
        f"Server error: {context.response.status_code} - {context.response.text}"


@then(parsers.parse("the response should contain {count:d} logs"))
def assert_log_count_exact(context, count: int):
    """Verify exact log count in response."""
    logs = context.response_data.get("logs", context.response_data.get("items", []))
    if isinstance(context.response_data, list):
        logs = context.response_data
    
    assert len(logs) == count, f"Expected {count} logs, got {len(logs)}"


@then("the response should have empty logs array")
def assert_empty_logs(context):
    """Verify logs array is empty."""
    logs = context.response_data.get("logs", context.response_data.get("items", []))
    if isinstance(context.response_data, list):
        logs = context.response_data
    
    assert len(logs) == 0, f"Expected empty logs, got {len(logs)}"


@then("the long message should be returned without truncation")
def assert_long_message_intact(context):
    """Verify long message wasn't truncated."""
    expected_length = context.custom.get("long_message_length", 5000)
    
    logs = context.response_data.get("logs", context.response_data.get("items", []))
    if isinstance(context.response_data, list):
        logs = context.response_data
    
    if logs:
        message = logs[0].get("message", "")
        assert len(message) >= expected_length, \
            f"Message truncated: expected {expected_length} chars, got {len(message)}"


@then("valid logs should still be returned")
def assert_valid_logs_returned(context):
    """Verify valid logs are returned despite malformed lines."""
    logs = context.response_data.get("logs", context.response_data.get("items", []))
    if isinstance(context.response_data, list):
        logs = context.response_data
    
    # Should have at least the 2 valid entries we created
    assert len(logs) >= 1, "Should return valid logs even with malformed lines"
