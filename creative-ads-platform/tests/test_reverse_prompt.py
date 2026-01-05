"""
Tests for Reverse Prompt Generation Module
"""

import pytest
from reverse_prompt.generate_prompt import (
    ReversePromptGenerator,
    PromptStyle,
    INDUSTRY_PROMPT_MODIFIERS,
    LAYOUT_PROMPT_COMPONENTS,
)


class TestPromptGenerator:
    """Tests for ReversePromptGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create a prompt generator instance."""
        return ReversePromptGenerator(
            project_id="test-project",
            use_ai_generation=False  # Use template-based for tests
        )
    
    @pytest.mark.asyncio
    async def test_generate_returns_dict(self, generator):
        """Test that generate returns expected structure."""
        features = {
            "layout_type": "hero",
            "focal_point": "product",
            "dominant_colors": [{"hex": "#2980b9", "percentage": 0.5}],
            "overall_brightness": 0.7,
            "contrast_level": 0.6,
            "typography": {"has_headline": True},
            "cta": {"detected": True, "text": "Shop Now"},
            "composition": {"rule_of_thirds": 0.8},
            "quality_score": 0.85
        }
        
        result = await generator.generate(
            features=features,
            industry="ecommerce"
        )
        
        assert "positive" in result
        assert "negative" in result
        assert "metadata" in result
        assert len(result["positive"]) > 0
    
    @pytest.mark.asyncio
    async def test_generate_includes_industry_modifiers(self, generator):
        """Test that industry modifiers are included."""
        features = {"layout_type": "hero"}
        
        result = await generator.generate(
            features=features,
            industry="finance"
        )
        
        # Finance should include professional language
        assert "professional" in result["positive"].lower() or \
               "trustworthy" in result["positive"].lower()
    
    @pytest.mark.asyncio
    async def test_generate_negative_prompt(self, generator):
        """Test negative prompt generation."""
        features = {"layout_type": "minimal"}
        
        result = await generator.generate(
            features=features,
            industry="saas",
            include_negative=True
        )
        
        assert len(result["negative"]) > 0
        assert "blurry" in result["negative"].lower() or \
               "low quality" in result["negative"].lower()
    
    @pytest.mark.asyncio
    async def test_generate_without_negative(self, generator):
        """Test generation without negative prompt."""
        features = {"layout_type": "grid"}
        
        result = await generator.generate(
            features=features,
            include_negative=False
        )
        
        assert result["negative"] == ""
    
    @pytest.mark.asyncio
    async def test_generate_batch(self, generator):
        """Test batch generation."""
        items = [
            {"features": {"layout_type": "hero"}, "industry": "finance"},
            {"features": {"layout_type": "split"}, "industry": "ecommerce"},
            {"features": {"layout_type": "minimal"}, "industry": "saas"},
        ]
        
        results = await generator.generate_batch(items)
        
        assert len(results) == 3
        assert all("positive" in r for r in results)
    
    def test_enhance_prompt(self, generator):
        """Test prompt enhancement."""
        base = "A professional advertisement"
        
        enhanced = generator.enhance_prompt(base, {
            "quality": True,
            "style": "corporate photography",
            "lighting": "studio",
            "aspect_ratio": "16:9"
        })
        
        assert "high quality" in enhanced.lower()
        assert "corporate photography" in enhanced
        assert "studio lighting" in enhanced
        assert "--ar 16:9" in enhanced
    
    def test_get_style_presets(self, generator):
        """Test style presets retrieval."""
        presets = generator.get_style_presets()
        
        assert "photorealistic" in presets
        assert "digital_art" in presets
        assert "minimalist" in presets
        assert "corporate" in presets
        assert "vibrant" in presets
        
        # Each preset should have suffix and negative
        for preset in presets.values():
            assert "suffix" in preset
            assert "negative" in preset


class TestIndustryModifiers:
    """Tests for industry prompt modifiers."""
    
    def test_all_industries_have_modifiers(self):
        """Test that all expected industries have modifiers."""
        expected_industries = [
            "finance", "ecommerce", "saas", "healthcare",
            "education", "entertainment", "food_beverage",
            "travel", "automotive", "real_estate", "fashion", "technology"
        ]
        
        for industry in expected_industries:
            assert industry in INDUSTRY_PROMPT_MODIFIERS
    
    def test_modifiers_have_required_keys(self):
        """Test that modifiers have required keys."""
        required_keys = ["tone", "elements", "colors", "avoid"]
        
        for industry, modifiers in INDUSTRY_PROMPT_MODIFIERS.items():
            for key in required_keys:
                assert key in modifiers, f"Missing {key} in {industry}"


class TestLayoutComponents:
    """Tests for layout prompt components."""
    
    def test_all_layouts_have_components(self):
        """Test that all expected layouts have components."""
        expected_layouts = [
            "hero", "grid", "split", "minimal",
            "product_focus", "lifestyle", "text_heavy"
        ]
        
        for layout in expected_layouts:
            assert layout in LAYOUT_PROMPT_COMPONENTS
    
    def test_components_are_strings(self):
        """Test that all components are non-empty strings."""
        for layout, component in LAYOUT_PROMPT_COMPONENTS.items():
            assert isinstance(component, str)
            assert len(component) > 0

