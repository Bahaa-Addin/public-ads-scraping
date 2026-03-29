"""
Step Definitions for Metrics Feature.

Tests dashboard metrics and time series including:
- Time series endpoint validation
- Dashboard metrics
- Distribution endpoints
- Edge cases (empty files, invalid data)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from pytest_bdd import scenarios, given, when, then, parsers

# Import common step definitions
from .common_steps import *

# Load scenarios from feature file
scenarios("../features/metrics.feature")


# ============================================
# Given Steps
# ============================================

@given(parsers.parse('time_series.json contains data for metric "{metric}"'))
def create_time_series_data(context, metric: str, data_manager, time_series_file):
    """Create time series data for a specific metric."""
    data_manager.backup_file(time_series_file)
    
    now = datetime.utcnow()
    data = {
        metric: [
            {"timestamp": (now - timedelta(hours=1)).isoformat(), "value": 10},
            {"timestamp": (now - timedelta(hours=2)).isoformat(), "value": 20},
            {"timestamp": now.isoformat(), "value": 30},
        ]
    }
    data_manager.write_json(time_series_file, data)


@given("time_series.json has valid data points")
def create_valid_time_series(context, data_manager, time_series_file):
    """Create valid time series data."""
    data_manager.backup_file(time_series_file)
    
    now = datetime.utcnow()
    data = {
        "assets_scraped": [
            {"timestamp": (now - timedelta(hours=1)).isoformat(), "value": 10},
            {"timestamp": now.isoformat(), "value": 20},
        ]
    }
    data_manager.write_json(time_series_file, data)


@given('time_series.json contains empty dict "{}"')
def create_empty_dict_time_series(context, data_manager, time_series_file):
    """Set time_series.json to empty dict."""
    data_manager.backup_file(time_series_file)
    data_manager.write_json(time_series_file, {})


@given('time_series.json contains empty array "[]"')
def create_empty_array_time_series(context, data_manager, time_series_file):
    """Set time_series.json to empty array."""
    data_manager.backup_file(time_series_file)
    # Write as array (legacy format)
    data_manager.write_json(time_series_file, [])


@given("all time series data points are older than 48 hours")
def create_old_time_series(context, data_manager, time_series_file):
    """Create time series with only old data."""
    data_manager.backup_file(time_series_file)
    
    old_time = datetime.utcnow() - timedelta(hours=72)
    data = {
        "assets_scraped": [
            {"timestamp": (old_time - timedelta(hours=1)).isoformat(), "value": 10},
            {"timestamp": old_time.isoformat(), "value": 20},
        ]
    }
    data_manager.write_json(time_series_file, data)


# ============================================
# Then Steps
# ============================================

@then(parsers.parse('each data point should have "timestamp" as ISO 8601 string'))
def assert_timestamp_format(context):
    """Verify timestamp fields are ISO 8601 formatted."""
    data = context.response_data.get("data", [])
    
    for point in data:
        ts = point.get("timestamp")
        assert ts is not None, "Data point missing timestamp"
        try:
            datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except ValueError:
            raise AssertionError(f"Invalid timestamp format: {ts}")


@then(parsers.parse('each data point should have "value" as number'))
def assert_value_numeric(context):
    """Verify value fields are numeric."""
    data = context.response_data.get("data", [])
    
    for point in data:
        value = point.get("value")
        assert isinstance(value, (int, float)), \
            f"Value should be numeric, got {type(value)}: {value}"
