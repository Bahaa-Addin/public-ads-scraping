"""
Feature Extraction Pipeline for Agentic Ads

Extracts structured features from ad creatives including:
- Layout type (hero, grid, split, minimal)
- Focal point (product, person, text, abstract)
- Typography analysis
- Color palette and contrast
- Visual complexity score
- CTA extraction and analysis
- Composition metrics

This module provides stubs for ML-ready pipelines that can be
expanded with actual model inference using Vertex AI or local models.
"""

import asyncio
import io
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import colorsys
from collections import Counter

logger = logging.getLogger(__name__)


# ============================================================================
# Enums and Types
# ============================================================================

class LayoutType(Enum):
    """Ad layout classification types."""
    HERO = "hero"           # Large hero image with text overlay
    GRID = "grid"           # Multi-image grid layout
    SPLIT = "split"         # Split screen (image/text sides)
    MINIMAL = "minimal"     # Minimal design, lots of whitespace
    CAROUSEL = "carousel"   # Multiple slides/frames
    COLLAGE = "collage"     # Overlapping elements collage
    PRODUCT_FOCUS = "product_focus"  # Product-centered layout
    LIFESTYLE = "lifestyle"  # Lifestyle/context imagery
    TEXT_HEAVY = "text_heavy"  # Primarily text-based


class FocalPoint(Enum):
    """Primary focal point of the creative."""
    PRODUCT = "product"
    PERSON = "person"
    TEXT = "text"
    ABSTRACT = "abstract"
    LOGO = "logo"
    SCENE = "scene"
    MULTIPLE = "multiple"


class VisualComplexity(Enum):
    """Visual complexity level."""
    SIMPLE = "simple"       # 1-2 elements
    MODERATE = "moderate"   # 3-5 elements
    COMPLEX = "complex"     # 6+ elements
    BUSY = "busy"           # Many overlapping elements


class ToneCategory(Enum):
    """Emotional tone/mood of the creative."""
    PROFESSIONAL = "professional"
    PLAYFUL = "playful"
    URGENT = "urgent"
    LUXURIOUS = "luxurious"
    FRIENDLY = "friendly"
    BOLD = "bold"
    CALM = "calm"
    ENERGETIC = "energetic"
    TRUSTWORTHY = "trustworthy"


class CTAType(Enum):
    """Call-to-action types."""
    SHOP_NOW = "shop_now"
    LEARN_MORE = "learn_more"
    SIGN_UP = "sign_up"
    GET_STARTED = "get_started"
    DOWNLOAD = "download"
    SUBSCRIBE = "subscribe"
    BOOK_NOW = "book_now"
    TRY_FREE = "try_free"
    CONTACT_US = "contact_us"
    CUSTOM = "custom"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ColorInfo:
    """Color information with multiple representations."""
    hex: str
    rgb: Tuple[int, int, int]
    hsl: Tuple[float, float, float]
    name: Optional[str] = None
    percentage: float = 0.0
    
    @classmethod
    def from_rgb(cls, r: int, g: int, b: int, percentage: float = 0.0) -> "ColorInfo":
        """Create ColorInfo from RGB values."""
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
        return cls(
            hex=hex_color,
            rgb=(r, g, b),
            hsl=(h * 360, s, l),
            percentage=percentage
        )


@dataclass
class TypographyInfo:
    """Typography analysis results."""
    estimated_font_styles: List[str]
    text_hierarchy_levels: int
    has_headline: bool
    has_subheadline: bool
    has_body_text: bool
    text_alignment: str  # left, center, right, justified
    estimated_readability: float  # 0-1 score


@dataclass
class CTAInfo:
    """Call-to-action analysis."""
    detected: bool
    type: Optional[CTAType]
    text: Optional[str]
    position: Optional[str]  # top, bottom, center, corner
    prominence: float  # 0-1 score
    color_contrast: float  # 0-1 contrast ratio


@dataclass
class CompositionInfo:
    """Composition analysis results."""
    rule_of_thirds_alignment: float  # 0-1 score
    symmetry_score: float  # 0-1 score
    balance_score: float  # 0-1 score
    white_space_ratio: float  # 0-1 ratio
    visual_flow_direction: str  # left-right, top-bottom, z-pattern, f-pattern


@dataclass
class ExtractedFeatures:
    """Complete extracted features for a creative asset."""
    # Core classifications
    layout_type: LayoutType
    focal_point: FocalPoint
    visual_complexity: VisualComplexity
    tone: ToneCategory
    
    # Color analysis
    dominant_colors: List[ColorInfo]
    color_palette_type: str  # monochromatic, complementary, analogous, triadic
    overall_brightness: float  # 0-1
    contrast_level: float  # 0-1
    
    # Typography
    typography: TypographyInfo
    
    # CTA
    cta: CTAInfo
    
    # Composition
    composition: CompositionInfo
    
    # Dimensions
    width: int
    height: int
    aspect_ratio: float
    
    # Additional metadata
    has_logo: bool
    has_human_face: bool
    has_product: bool
    text_regions_count: int
    estimated_text_coverage: float  # 0-1
    
    # Quality metrics
    sharpness_score: float  # 0-1
    noise_level: float  # 0-1
    overall_quality_score: float  # 0-1
    
    # Raw feature vector for ML
    feature_vector: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "layout_type": self.layout_type.value,
            "focal_point": self.focal_point.value,
            "visual_complexity": self.visual_complexity.value,
            "tone": self.tone.value,
            "dominant_colors": [
                {"hex": c.hex, "percentage": c.percentage}
                for c in self.dominant_colors
            ],
            "color_palette_type": self.color_palette_type,
            "overall_brightness": self.overall_brightness,
            "contrast_level": self.contrast_level,
            "typography": {
                "font_styles": self.typography.estimated_font_styles,
                "hierarchy_levels": self.typography.text_hierarchy_levels,
                "readability": self.typography.estimated_readability,
            },
            "cta": {
                "detected": self.cta.detected,
                "type": self.cta.type.value if self.cta.type else None,
                "text": self.cta.text,
                "prominence": self.cta.prominence,
            },
            "composition": {
                "rule_of_thirds": self.composition.rule_of_thirds_alignment,
                "symmetry": self.composition.symmetry_score,
                "balance": self.composition.balance_score,
                "white_space": self.composition.white_space_ratio,
            },
            "dimensions": {
                "width": self.width,
                "height": self.height,
                "aspect_ratio": self.aspect_ratio,
            },
            "has_logo": self.has_logo,
            "has_human_face": self.has_human_face,
            "has_product": self.has_product,
            "text_coverage": self.estimated_text_coverage,
            "quality_score": self.overall_quality_score,
        }


# ============================================================================
# Feature Extractor
# ============================================================================

class FeatureExtractor:
    """
    ML-ready feature extraction pipeline for creative assets.
    
    This implementation provides stub methods that can be expanded
    with actual model inference using:
    - Google Cloud Vision API
    - Vertex AI custom models
    - Local ML models (PyTorch/TensorFlow)
    """
    
    def __init__(
        self,
        use_cloud_vision: bool = False,
        use_vertex_ai: bool = False,
        vertex_ai_endpoint: Optional[str] = None
    ):
        self.use_cloud_vision = use_cloud_vision
        self.use_vertex_ai = use_vertex_ai
        self.vertex_ai_endpoint = vertex_ai_endpoint
        
        # Initialize clients if needed
        self._vision_client = None
        self._vertex_client = None
        
    async def extract(
        self,
        image_source: str,
        asset_type: str = "image"
    ) -> Dict[str, Any]:
        """
        Extract features from an image URL or file path.
        
        Args:
            image_source: URL or file path to the image
            asset_type: Type of asset (image, video_frame)
            
        Returns:
            Dictionary of extracted features
        """
        logger.info(f"Extracting features from: {image_source}")
        
        try:
            # Load and preprocess image
            image_data = await self._load_image(image_source)
            
            if image_data is None:
                return self._get_default_features()
            
            # Run feature extraction pipeline
            features = await self._extract_all_features(image_data)
            
            return features.to_dict()
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}", exc_info=True)
            return self._get_default_features()
    
    async def _load_image(self, source: str) -> Optional[bytes]:
        """Load image from URL or file path."""
        try:
            if source.startswith(('http://', 'https://')):
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(source, timeout=30) as response:
                        if response.status == 200:
                            return await response.read()
            else:
                with open(source, 'rb') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
        return None
    
    async def _extract_all_features(self, image_data: bytes) -> ExtractedFeatures:
        """Run all feature extraction methods."""
        # Get image dimensions
        width, height = await self._get_dimensions(image_data)
        
        # Extract individual features (in parallel where possible)
        colors = await self._extract_colors(image_data)
        layout = await self._detect_layout(image_data, width, height)
        focal_point = await self._detect_focal_point(image_data)
        typography = await self._analyze_typography(image_data)
        cta = await self._detect_cta(image_data)
        composition = await self._analyze_composition(image_data, width, height)
        complexity = await self._assess_complexity(image_data)
        tone = await self._detect_tone(colors, layout)
        
        # Object detection results
        has_logo = await self._detect_logo(image_data)
        has_face = await self._detect_face(image_data)
        has_product = await self._detect_product(image_data)
        
        # Quality metrics
        quality = await self._assess_quality(image_data)
        
        # Generate feature vector for ML
        feature_vector = self._generate_feature_vector(
            layout, focal_point, complexity, colors, typography, cta
        )
        
        return ExtractedFeatures(
            layout_type=layout,
            focal_point=focal_point,
            visual_complexity=complexity,
            tone=tone,
            dominant_colors=colors,
            color_palette_type=self._classify_palette(colors),
            overall_brightness=self._calculate_brightness(colors),
            contrast_level=self._calculate_contrast(colors),
            typography=typography,
            cta=cta,
            composition=composition,
            width=width,
            height=height,
            aspect_ratio=width / height if height > 0 else 1.0,
            has_logo=has_logo,
            has_human_face=has_face,
            has_product=has_product,
            text_regions_count=typography.text_hierarchy_levels,
            estimated_text_coverage=0.2,  # Stub value
            sharpness_score=quality.get('sharpness', 0.8),
            noise_level=quality.get('noise', 0.1),
            overall_quality_score=quality.get('overall', 0.85),
            feature_vector=feature_vector
        )
    
    async def _get_dimensions(self, image_data: bytes) -> Tuple[int, int]:
        """Get image dimensions."""
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_data))
            return img.size
        except ImportError:
            # Fallback: parse header for common formats
            return (1200, 628)  # Default ad dimensions
        except Exception:
            return (1200, 628)
    
    async def _extract_colors(self, image_data: bytes) -> List[ColorInfo]:
        """Extract dominant colors from the image."""
        # Stub implementation - returns placeholder colors
        # In production: use k-means clustering on image pixels
        return [
            ColorInfo.from_rgb(41, 128, 185, 0.35),   # Blue
            ColorInfo.from_rgb(255, 255, 255, 0.30),  # White
            ColorInfo.from_rgb(44, 62, 80, 0.20),    # Dark gray
            ColorInfo.from_rgb(231, 76, 60, 0.10),   # Red accent
            ColorInfo.from_rgb(46, 204, 113, 0.05),  # Green accent
        ]
    
    async def _detect_layout(
        self,
        image_data: bytes,
        width: int,
        height: int
    ) -> LayoutType:
        """Detect the layout type of the creative."""
        # Stub implementation
        # In production: use CNN classifier or Vertex AI
        aspect_ratio = width / height if height > 0 else 1.0
        
        if aspect_ratio > 2.0:
            return LayoutType.HERO
        elif aspect_ratio < 0.8:
            return LayoutType.PRODUCT_FOCUS
        else:
            return LayoutType.SPLIT
    
    async def _detect_focal_point(self, image_data: bytes) -> FocalPoint:
        """Detect the primary focal point of the creative."""
        # Stub implementation
        # In production: use object detection + saliency maps
        return FocalPoint.PRODUCT
    
    async def _analyze_typography(self, image_data: bytes) -> TypographyInfo:
        """Analyze typography in the creative."""
        # Stub implementation
        # In production: use OCR + font detection
        return TypographyInfo(
            estimated_font_styles=["sans-serif", "bold"],
            text_hierarchy_levels=2,
            has_headline=True,
            has_subheadline=True,
            has_body_text=False,
            text_alignment="center",
            estimated_readability=0.85
        )
    
    async def _detect_cta(self, image_data: bytes) -> CTAInfo:
        """Detect and analyze call-to-action elements."""
        # Stub implementation
        # In production: use OCR + button detection
        return CTAInfo(
            detected=True,
            type=CTAType.SHOP_NOW,
            text="Shop Now",
            position="bottom",
            prominence=0.8,
            color_contrast=0.9
        )
    
    async def _analyze_composition(
        self,
        image_data: bytes,
        width: int,
        height: int
    ) -> CompositionInfo:
        """Analyze the composition of the creative."""
        # Stub implementation
        # In production: use grid analysis + element detection
        return CompositionInfo(
            rule_of_thirds_alignment=0.75,
            symmetry_score=0.6,
            balance_score=0.8,
            white_space_ratio=0.25,
            visual_flow_direction="left-right"
        )
    
    async def _assess_complexity(self, image_data: bytes) -> VisualComplexity:
        """Assess the visual complexity of the creative."""
        # Stub implementation
        # In production: use edge detection + element counting
        return VisualComplexity.MODERATE
    
    async def _detect_tone(
        self,
        colors: List[ColorInfo],
        layout: LayoutType
    ) -> ToneCategory:
        """Detect the emotional tone/mood of the creative."""
        # Stub implementation based on color and layout
        # In production: use multimodal analysis
        avg_brightness = self._calculate_brightness(colors)
        
        if avg_brightness > 0.7:
            return ToneCategory.FRIENDLY
        elif avg_brightness < 0.3:
            return ToneCategory.BOLD
        else:
            return ToneCategory.PROFESSIONAL
    
    async def _detect_logo(self, image_data: bytes) -> bool:
        """Detect if a logo is present in the image."""
        # Stub - return True as most ads have logos
        return True
    
    async def _detect_face(self, image_data: bytes) -> bool:
        """Detect if human faces are present in the image."""
        # Stub implementation
        # In production: use face detection API
        return False
    
    async def _detect_product(self, image_data: bytes) -> bool:
        """Detect if products are present in the image."""
        # Stub implementation
        return True
    
    async def _assess_quality(self, image_data: bytes) -> Dict[str, float]:
        """Assess the quality metrics of the image."""
        # Stub implementation
        return {
            "sharpness": 0.85,
            "noise": 0.1,
            "overall": 0.88
        }
    
    def _classify_palette(self, colors: List[ColorInfo]) -> str:
        """Classify the color palette type."""
        if len(colors) < 2:
            return "monochromatic"
        
        # Get hues
        hues = [c.hsl[0] for c in colors if c.percentage > 0.05]
        
        if not hues:
            return "neutral"
        
        hue_range = max(hues) - min(hues)
        
        if hue_range < 30:
            return "monochromatic"
        elif hue_range < 60:
            return "analogous"
        elif 150 < hue_range < 210:
            return "complementary"
        else:
            return "triadic"
    
    def _calculate_brightness(self, colors: List[ColorInfo]) -> float:
        """Calculate overall brightness from colors."""
        if not colors:
            return 0.5
        
        weighted_brightness = sum(
            c.hsl[2] * c.percentage for c in colors
        )
        total_percentage = sum(c.percentage for c in colors)
        
        return weighted_brightness / total_percentage if total_percentage > 0 else 0.5
    
    def _calculate_contrast(self, colors: List[ColorInfo]) -> float:
        """Calculate contrast level from colors."""
        if len(colors) < 2:
            return 0.5
        
        lightnesses = [c.hsl[2] for c in colors if c.percentage > 0.05]
        
        if len(lightnesses) < 2:
            return 0.5
        
        return max(lightnesses) - min(lightnesses)
    
    def _generate_feature_vector(
        self,
        layout: LayoutType,
        focal_point: FocalPoint,
        complexity: VisualComplexity,
        colors: List[ColorInfo],
        typography: TypographyInfo,
        cta: CTAInfo
    ) -> List[float]:
        """Generate a numerical feature vector for ML models."""
        vector = []
        
        # One-hot encode layout type
        layout_types = list(LayoutType)
        vector.extend([1.0 if l == layout else 0.0 for l in layout_types])
        
        # One-hot encode focal point
        focal_types = list(FocalPoint)
        vector.extend([1.0 if f == focal_point else 0.0 for f in focal_types])
        
        # Complexity as ordinal
        complexity_map = {
            VisualComplexity.SIMPLE: 0.25,
            VisualComplexity.MODERATE: 0.5,
            VisualComplexity.COMPLEX: 0.75,
            VisualComplexity.BUSY: 1.0
        }
        vector.append(complexity_map.get(complexity, 0.5))
        
        # Color features
        vector.append(self._calculate_brightness(colors))
        vector.append(self._calculate_contrast(colors))
        
        # Add dominant color RGB normalized
        if colors:
            for i in range(min(3, len(colors))):
                vector.extend([c/255 for c in colors[i].rgb])
        
        # Typography features
        vector.append(float(typography.has_headline))
        vector.append(float(typography.has_subheadline))
        vector.append(typography.estimated_readability)
        
        # CTA features
        vector.append(float(cta.detected))
        vector.append(cta.prominence)
        
        return vector
    
    def _get_default_features(self) -> Dict[str, Any]:
        """Return default features when extraction fails."""
        return {
            "layout_type": "unknown",
            "focal_point": "unknown",
            "visual_complexity": "unknown",
            "error": True
        }


# ============================================================================
# Industry Classifier
# ============================================================================

class IndustryClassifier:
    """
    Classify ads into industry categories based on extracted features.
    
    Uses a combination of:
    - Visual features (colors, layout, imagery)
    - Text content (OCR results, CTA text)
    - Metadata (advertiser info, keywords)
    """
    
    # Industry keywords for rule-based classification
    INDUSTRY_KEYWORDS = {
        "finance": [
            "bank", "loan", "credit", "invest", "money", "financial",
            "insurance", "mortgage", "savings", "wealth", "trading"
        ],
        "ecommerce": [
            "shop", "buy", "sale", "discount", "price", "order",
            "delivery", "cart", "checkout", "deal", "offer"
        ],
        "saas": [
            "software", "platform", "cloud", "app", "tool", "solution",
            "dashboard", "analytics", "automate", "workflow", "integrate"
        ],
        "healthcare": [
            "health", "medical", "doctor", "patient", "care", "wellness",
            "therapy", "treatment", "clinic", "hospital", "medicine"
        ],
        "education": [
            "learn", "course", "training", "education", "school", "university",
            "student", "degree", "online learning", "certification"
        ],
        "entertainment": [
            "watch", "stream", "movie", "game", "play", "music",
            "show", "series", "entertainment", "fun"
        ],
        "food_beverage": [
            "food", "drink", "restaurant", "recipe", "taste", "fresh",
            "organic", "delivery", "order food", "menu"
        ],
        "travel": [
            "travel", "trip", "hotel", "flight", "vacation", "booking",
            "destination", "adventure", "explore", "tourism"
        ],
        "automotive": [
            "car", "vehicle", "drive", "auto", "lease", "dealership",
            "test drive", "model", "mpg", "electric"
        ],
        "real_estate": [
            "home", "property", "rent", "buy", "apartment", "house",
            "real estate", "listing", "mortgage", "neighborhood"
        ],
        "fashion": [
            "style", "fashion", "clothing", "wear", "outfit", "collection",
            "designer", "trend", "dress", "accessory"
        ],
        "technology": [
            "tech", "device", "gadget", "innovation", "smart", "digital",
            "AI", "automation", "IoT", "security"
        ]
    }
    
    def __init__(self, use_ml_model: bool = False):
        self.use_ml_model = use_ml_model
        self._model = None
    
    async def classify(
        self,
        features: Dict[str, Any],
        text_content: Optional[str] = None,
        advertiser_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Classify the industry of an ad.
        
        Args:
            features: Extracted visual features
            text_content: Optional OCR text from the ad
            advertiser_info: Optional advertiser metadata
            
        Returns:
            Industry category string
        """
        logger.info("Classifying industry")
        
        if self.use_ml_model and self._model:
            return await self._ml_classify(features, text_content)
        
        return self._rule_based_classify(features, text_content, advertiser_info)
    
    def _rule_based_classify(
        self,
        features: Dict[str, Any],
        text_content: Optional[str],
        advertiser_info: Optional[Dict[str, Any]]
    ) -> str:
        """Rule-based industry classification."""
        scores: Dict[str, float] = Counter()
        
        # Check text content for keywords
        if text_content:
            text_lower = text_content.lower()
            for industry, keywords in self.INDUSTRY_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        scores[industry] += 1.0
        
        # Check advertiser info
        if advertiser_info:
            advertiser_name = advertiser_info.get("name", "").lower()
            for industry, keywords in self.INDUSTRY_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in advertiser_name:
                        scores[industry] += 2.0  # Higher weight for advertiser name
        
        # Visual feature heuristics
        if features:
            cta = features.get("cta", {})
            cta_text = cta.get("text", "").lower() if cta else ""
            
            if "shop" in cta_text or "buy" in cta_text:
                scores["ecommerce"] += 1.5
            elif "learn" in cta_text or "start" in cta_text:
                scores["saas"] += 1.0
            elif "book" in cta_text:
                scores["travel"] += 1.0
            
            # Color-based heuristics
            colors = features.get("dominant_colors", [])
            if colors:
                # Blue often indicates finance/tech
                for color in colors:
                    hex_color = color.get("hex", "").lower()
                    if hex_color.startswith("#0") or hex_color.startswith("#1"):
                        scores["finance"] += 0.3
                        scores["technology"] += 0.3
        
        # Return highest scoring industry or "other"
        if scores:
            return scores.most_common(1)[0][0]
        
        return "other"
    
    async def _ml_classify(
        self,
        features: Dict[str, Any],
        text_content: Optional[str]
    ) -> str:
        """ML-based industry classification (stub)."""
        # In production: call Vertex AI endpoint
        logger.info("ML classification requested but not implemented")
        return "other"
    
    def get_industry_tags(
        self,
        industry: str,
        features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get detailed industry tags and sub-categories."""
        tags = {
            "primary_industry": industry,
            "sub_categories": [],
            "cta_type": None,
            "focal_object": None,
            "tone": None,
            "format": None
        }
        
        # CTA type
        cta = features.get("cta", {})
        if cta and cta.get("detected"):
            tags["cta_type"] = cta.get("type")
        
        # Focal object
        tags["focal_object"] = features.get("focal_point")
        
        # Tone
        tags["tone"] = features.get("tone")
        
        # Format based on dimensions
        dims = features.get("dimensions", {})
        if dims:
            aspect_ratio = dims.get("aspect_ratio", 1.0)
            if aspect_ratio > 1.5:
                tags["format"] = "banner"
            elif aspect_ratio < 0.75:
                tags["format"] = "story"
            else:
                tags["format"] = "square"
        
        return tags

