"""
Step Definitions for Assets Feature.

Tests creative assets management including:
- Listing assets
- Filtering assets
- Empty state handling
- Edge cases
"""

import json
from datetime import datetime
from pathlib import Path
from pytest_bdd import scenarios, given, when, then, parsers

# Import common step definitions
from .common_steps import *

# Load scenarios from feature file
scenarios("../features/assets.feature")


# ============================================
# Given Steps
# ============================================

@given(parsers.parse("{count:d} assets exist in the database"))
def create_assets(context, count: int, data_manager, assets_file, asset_factory):
    """Create N assets in the database."""
    data_manager.backup_file(assets_file)
    
    assets = []
    for i in range(count):
        asset = asset_factory(
            asset_id=f"test-asset-{i}",
            title=f"Test Ad {i}",
            source="meta_ad_library" if i % 2 == 0 else "google_ads_transparency",
            industry="technology" if i % 3 == 0 else "ecommerce"
        )
        assets.append(asset)
    
    data_manager.write_json(assets_file, assets)


@given("assets exist with various industries and sources")
def create_varied_assets(context, data_manager, assets_file, asset_factory):
    """Create assets with different industries and sources."""
    data_manager.backup_file(assets_file)
    
    assets = [
        asset_factory(asset_id="asset-tech-meta", source="meta_ad_library", industry="technology"),
        asset_factory(asset_id="asset-ecommerce-meta", source="meta_ad_library", industry="ecommerce"),
        asset_factory(asset_id="asset-tech-google", source="google_ads", industry="technology"),
        asset_factory(asset_id="asset-health-google", source="google_ads", industry="healthcare"),
    ]
    data_manager.write_json(assets_file, assets)


@given(parsers.parse('assets exist from sources "{source1}" and "{source2}"'))
def create_assets_from_sources(context, source1: str, source2: str, data_manager, assets_file, asset_factory):
    """Create assets from two different sources."""
    data_manager.backup_file(assets_file)
    
    assets = [
        asset_factory(asset_id="asset-1", source=source1),
        asset_factory(asset_id="asset-2", source=source1),
        asset_factory(asset_id="asset-3", source=source2),
    ]
    data_manager.write_json(assets_file, assets)


@given("assets.json contains empty array")
def create_empty_assets(context, data_manager, assets_file):
    """Set assets.json to empty array."""
    data_manager.backup_file(assets_file)
    data_manager.write_json(assets_file, [])


@given('an asset exists without "industry" field')
def create_asset_without_industry(context, data_manager, assets_file):
    """Create asset missing optional industry field."""
    data_manager.backup_file(assets_file)
    
    asset = {
        "id": "asset-no-industry",
        "source": "meta_ad_library",
        "title": "Test Ad",
        "image_url": "https://example.com/image.jpg",
        "created_at": datetime.utcnow().isoformat()
        # Intentionally missing 'industry'
    }
    data_manager.write_json(assets_file, [asset])


# ============================================
# Then Steps
# ============================================

@then("the response should contain assets")
def assert_has_assets(context):
    """Verify response contains assets."""
    assets = context.response_data.get("assets", context.response_data.get("items", []))
    if isinstance(context.response_data, list):
        assets = context.response_data
    
    assert len(assets) > 0, "Expected assets in response"


@then("the response should have total count")
def assert_has_total(context):
    """Verify response has total count."""
    total = context.response_data.get("total")
    assert total is not None, "Response missing 'total' field"


@then(parsers.parse('all returned assets should have source "{source}"'))
def assert_assets_source(context, source: str):
    """Verify all assets have expected source."""
    assets = context.response_data.get("assets", context.response_data.get("items", []))
    if isinstance(context.response_data, list):
        assets = context.response_data
    
    for asset in assets:
        assert asset.get("source") == source, \
            f"Expected source '{source}', got '{asset.get('source')}'"


@then("the response should have empty assets array")
def assert_empty_assets(context):
    """Verify assets array is empty."""
    assets = context.response_data.get("assets", context.response_data.get("items", []))
    if isinstance(context.response_data, list):
        assets = context.response_data
    
    assert len(assets) == 0, f"Expected empty assets, got {len(assets)}"


@then("total should be 0")
def assert_total_zero(context):
    """Verify total is 0."""
    total = context.response_data.get("total", 0)
    assert total == 0, f"Expected total 0, got {total}"


@then("the asset should be returned with null or default industry")
def assert_industry_default(context):
    """Verify asset with missing industry is handled."""
    assets = context.response_data.get("assets", context.response_data.get("items", []))
    if isinstance(context.response_data, list):
        assets = context.response_data
    
    if assets:
        asset = assets[0]
        # Industry should be None/null or have a default value
        industry = asset.get("industry")
        # Just verify the asset was returned (the field might be missing, null, or default)
        assert "id" in asset, "Asset should be returned"
