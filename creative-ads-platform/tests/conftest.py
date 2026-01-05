"""
Pytest Configuration and Fixtures
"""

import os
import sys
import pytest
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_features():
    """Sample extracted features for testing."""
    return {
        "layout_type": "hero",
        "focal_point": "product",
        "visual_complexity": "moderate",
        "tone": "professional",
        "dominant_colors": [
            {"hex": "#2980b9", "percentage": 0.35},
            {"hex": "#ffffff", "percentage": 0.30},
            {"hex": "#2c3e50", "percentage": 0.20},
        ],
        "color_palette_type": "complementary",
        "overall_brightness": 0.65,
        "contrast_level": 0.7,
        "typography": {
            "font_styles": ["sans-serif", "bold"],
            "hierarchy_levels": 2,
            "readability": 0.85
        },
        "cta": {
            "detected": True,
            "type": "shop_now",
            "text": "Shop Now",
            "prominence": 0.8
        },
        "composition": {
            "rule_of_thirds": 0.75,
            "symmetry": 0.6,
            "balance": 0.8,
            "white_space": 0.25
        },
        "dimensions": {
            "width": 1200,
            "height": 628,
            "aspect_ratio": 1.91
        },
        "has_logo": True,
        "has_human_face": False,
        "has_product": True,
        "text_coverage": 0.2,
        "quality_score": 0.88
    }


@pytest.fixture
def sample_asset():
    """Sample creative asset for testing."""
    return {
        "id": "test-asset-001",
        "source": "meta_ad_library",
        "source_url": "https://facebook.com/ads/library/123",
        "image_url": "https://example.com/ad.jpg",
        "asset_type": "image",
        "advertiser_name": "Test Advertiser",
        "title": "Amazing Product Sale",
        "description": "Get 50% off our best products today!"
    }


@pytest.fixture
def mock_firestore():
    """Mock Firestore client for testing."""
    from firestore.firestore_client import MockFirestoreClient
    return MockFirestoreClient()

