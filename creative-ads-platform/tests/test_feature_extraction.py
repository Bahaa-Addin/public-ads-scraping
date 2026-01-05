"""
Tests for Feature Extraction Module
"""

import pytest
from feature_extraction.extract_features import (
    FeatureExtractor,
    IndustryClassifier,
    LayoutType,
    FocalPoint,
    VisualComplexity,
    ColorInfo,
)


class TestColorInfo:
    """Tests for ColorInfo dataclass."""
    
    def test_from_rgb(self):
        """Test creating ColorInfo from RGB values."""
        color = ColorInfo.from_rgb(255, 0, 0, 0.5)
        
        assert color.hex == "#ff0000"
        assert color.rgb == (255, 0, 0)
        assert color.percentage == 0.5
        assert 0 <= color.hsl[0] <= 360
    
    def test_from_rgb_black(self):
        """Test black color."""
        color = ColorInfo.from_rgb(0, 0, 0)
        assert color.hex == "#000000"
    
    def test_from_rgb_white(self):
        """Test white color."""
        color = ColorInfo.from_rgb(255, 255, 255)
        assert color.hex == "#ffffff"


class TestFeatureExtractor:
    """Tests for FeatureExtractor class."""
    
    @pytest.fixture
    def extractor(self):
        """Create a feature extractor instance."""
        return FeatureExtractor()
    
    @pytest.mark.asyncio
    async def test_extract_returns_dict(self, extractor):
        """Test that extract returns a dictionary."""
        # Using a non-existent URL will return default features
        result = await extractor.extract("http://example.com/nonexistent.jpg")
        
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_default_features_on_error(self, extractor):
        """Test that default features are returned on error."""
        result = await extractor.extract("invalid://url")
        
        assert "error" in result or "layout_type" in result
    
    def test_classify_palette_monochromatic(self, extractor):
        """Test monochromatic palette classification."""
        colors = [
            ColorInfo.from_rgb(100, 100, 100, 0.5),
            ColorInfo.from_rgb(120, 120, 120, 0.3),
            ColorInfo.from_rgb(80, 80, 80, 0.2),
        ]
        
        result = extractor._classify_palette(colors)
        assert result in ["monochromatic", "neutral"]
    
    def test_calculate_brightness(self, extractor):
        """Test brightness calculation."""
        # White colors should have high brightness
        colors = [ColorInfo.from_rgb(255, 255, 255, 1.0)]
        brightness = extractor._calculate_brightness(colors)
        assert brightness > 0.9
        
        # Black colors should have low brightness
        colors = [ColorInfo.from_rgb(0, 0, 0, 1.0)]
        brightness = extractor._calculate_brightness(colors)
        assert brightness < 0.1
    
    def test_calculate_contrast(self, extractor):
        """Test contrast calculation."""
        # High contrast between black and white
        colors = [
            ColorInfo.from_rgb(0, 0, 0, 0.5),
            ColorInfo.from_rgb(255, 255, 255, 0.5),
        ]
        contrast = extractor._calculate_contrast(colors)
        assert contrast > 0.8
        
        # Low contrast with similar colors
        colors = [
            ColorInfo.from_rgb(100, 100, 100, 0.5),
            ColorInfo.from_rgb(110, 110, 110, 0.5),
        ]
        contrast = extractor._calculate_contrast(colors)
        assert contrast < 0.2
    
    def test_generate_feature_vector(self, extractor):
        """Test feature vector generation."""
        from feature_extraction.extract_features import (
            TypographyInfo,
            CTAInfo,
            CTAType,
        )
        
        typography = TypographyInfo(
            estimated_font_styles=["sans-serif"],
            text_hierarchy_levels=2,
            has_headline=True,
            has_subheadline=True,
            has_body_text=False,
            text_alignment="center",
            estimated_readability=0.8
        )
        
        cta = CTAInfo(
            detected=True,
            type=CTAType.SHOP_NOW,
            text="Shop Now",
            position="bottom",
            prominence=0.8,
            color_contrast=0.9
        )
        
        colors = [ColorInfo.from_rgb(100, 100, 200, 0.5)]
        
        vector = extractor._generate_feature_vector(
            LayoutType.HERO,
            FocalPoint.PRODUCT,
            VisualComplexity.MODERATE,
            colors,
            typography,
            cta
        )
        
        assert isinstance(vector, list)
        assert len(vector) > 0
        assert all(isinstance(v, (int, float)) for v in vector)


class TestIndustryClassifier:
    """Tests for IndustryClassifier class."""
    
    @pytest.fixture
    def classifier(self):
        """Create an industry classifier instance."""
        return IndustryClassifier()
    
    @pytest.mark.asyncio
    async def test_classify_finance(self, classifier):
        """Test finance industry classification."""
        result = await classifier.classify(
            features={},
            text_content="Get the best loan rates for your mortgage"
        )
        
        assert result == "finance"
    
    @pytest.mark.asyncio
    async def test_classify_ecommerce(self, classifier):
        """Test e-commerce industry classification."""
        result = await classifier.classify(
            features={
                "cta": {"detected": True, "text": "Shop Now"}
            },
            text_content="Buy now and save 50%"
        )
        
        assert result == "ecommerce"
    
    @pytest.mark.asyncio
    async def test_classify_saas(self, classifier):
        """Test SaaS industry classification."""
        result = await classifier.classify(
            features={},
            text_content="Cloud software platform for automation"
        )
        
        assert result == "saas"
    
    @pytest.mark.asyncio
    async def test_classify_unknown(self, classifier):
        """Test unknown industry classification."""
        result = await classifier.classify(
            features={},
            text_content=""
        )
        
        assert result == "other"
    
    def test_get_industry_tags(self, classifier):
        """Test industry tag generation."""
        features = {
            "focal_point": "product",
            "tone": "professional",
            "cta": {"detected": True, "type": "shop_now"},
            "dimensions": {"aspect_ratio": 2.0}
        }
        
        tags = classifier.get_industry_tags("ecommerce", features)
        
        assert tags["primary_industry"] == "ecommerce"
        assert tags["focal_object"] == "product"
        assert tags["format"] == "banner"

