"""
Rules Engine for Reverse Prompt Generation

A deterministic, rule-based system for generating reverse prompts.
This is the primary method for LOCAL mode prompt generation.

The rules engine:
1. Analyzes extracted features
2. Applies industry-specific rules
3. Generates consistent, reproducible prompts
4. Does NOT require any AI/LLM service

This ensures the platform can run fully offline with zero cloud dependencies.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# Rule Definitions
# ============================================================================

class RuleCategory(Enum):
    """Categories of prompt generation rules."""
    LAYOUT = "layout"
    COLOR = "color"
    TYPOGRAPHY = "typography"
    COMPOSITION = "composition"
    INDUSTRY = "industry"
    QUALITY = "quality"
    CTA = "cta"
    MOOD = "mood"


@dataclass
class Rule:
    """A single prompt generation rule."""
    name: str
    category: RuleCategory
    condition: str  # Python expression to evaluate
    positive_output: str
    negative_output: Optional[str] = None
    priority: int = 0  # Higher = applied first
    
    def evaluate(self, features: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Evaluate the rule against features.
        
        Returns: (matches, positive_text, negative_text)
        """
        try:
            # Create evaluation context with features
            context = {"features": features}
            context.update(features)
            
            # Evaluate condition
            result = eval(self.condition, {"__builtins__": {}}, context)
            
            if result:
                return (True, self.positive_output, self.negative_output)
            
        except Exception as e:
            logger.debug(f"Rule '{self.name}' evaluation error: {e}")
        
        return (False, None, None)


# ============================================================================
# Rule Sets
# ============================================================================

LAYOUT_RULES = [
    Rule(
        name="hero_layout",
        category=RuleCategory.LAYOUT,
        condition="features.get('layout_type') == 'hero'",
        positive_output="large hero image composition, prominent central subject, text overlay area",
        negative_output="cluttered multi-image layout",
        priority=10,
    ),
    Rule(
        name="grid_layout",
        category=RuleCategory.LAYOUT,
        condition="features.get('layout_type') == 'grid'",
        positive_output="multi-panel grid layout, organized sections, visual hierarchy",
        negative_output="single image, unstructured",
        priority=10,
    ),
    Rule(
        name="split_layout",
        category=RuleCategory.LAYOUT,
        condition="features.get('layout_type') == 'split'",
        positive_output="split screen composition, dual focus areas, balanced design",
        negative_output="single focus point",
        priority=10,
    ),
    Rule(
        name="minimal_layout",
        category=RuleCategory.LAYOUT,
        condition="features.get('layout_type') == 'minimal'",
        positive_output="minimalist design, ample white space, focused subject",
        negative_output="busy, cluttered, complex",
        priority=10,
    ),
    Rule(
        name="product_focus",
        category=RuleCategory.LAYOUT,
        condition="features.get('layout_type') == 'product_focus'",
        positive_output="product-centered composition, clean background, detail visibility",
        negative_output="distracting background elements",
        priority=10,
    ),
    Rule(
        name="lifestyle_layout",
        category=RuleCategory.LAYOUT,
        condition="features.get('layout_type') == 'lifestyle'",
        positive_output="lifestyle context, environmental setting, natural staging",
        negative_output="studio shot, isolated product",
        priority=10,
    ),
]

COLOR_RULES = [
    Rule(
        name="bright_image",
        category=RuleCategory.COLOR,
        condition="features.get('overall_brightness', 0.5) > 0.7",
        positive_output="bright, well-lit, high key lighting",
        negative_output="dark, underexposed",
        priority=5,
    ),
    Rule(
        name="dark_moody",
        category=RuleCategory.COLOR,
        condition="features.get('overall_brightness', 0.5) < 0.3",
        positive_output="dark, moody lighting, dramatic shadows",
        negative_output="overexposed, washed out",
        priority=5,
    ),
    Rule(
        name="high_contrast",
        category=RuleCategory.COLOR,
        condition="features.get('contrast_level', 0.5) > 0.7",
        positive_output="high contrast, bold tones, strong shadows",
        negative_output="flat, low contrast",
        priority=5,
    ),
    Rule(
        name="monochromatic",
        category=RuleCategory.COLOR,
        condition="features.get('color_palette_type') == 'monochromatic'",
        positive_output="monochromatic color scheme, cohesive palette",
        negative_output="multi-colored, rainbow",
        priority=5,
    ),
    Rule(
        name="complementary",
        category=RuleCategory.COLOR,
        condition="features.get('color_palette_type') == 'complementary'",
        positive_output="complementary colors, dynamic color contrast",
        negative_output="monotone",
        priority=5,
    ),
]

COMPOSITION_RULES = [
    Rule(
        name="rule_of_thirds",
        category=RuleCategory.COMPOSITION,
        condition="features.get('composition', {}).get('rule_of_thirds', 0) > 0.7",
        positive_output="rule of thirds composition, balanced framing",
        negative_output="centered, static composition",
        priority=3,
    ),
    Rule(
        name="symmetrical",
        category=RuleCategory.COMPOSITION,
        condition="features.get('composition', {}).get('symmetry', 0) > 0.7",
        positive_output="symmetrical layout, centered design",
        negative_output="asymmetric, unbalanced",
        priority=3,
    ),
    Rule(
        name="high_whitespace",
        category=RuleCategory.COMPOSITION,
        condition="features.get('composition', {}).get('white_space', 0) > 0.4",
        positive_output="generous white space, breathing room",
        negative_output="crowded, no margins",
        priority=3,
    ),
]

CTA_RULES = [
    Rule(
        name="cta_present",
        category=RuleCategory.CTA,
        condition="features.get('cta', {}).get('detected', False)",
        positive_output="clear call-to-action button, prominent CTA",
        negative_output=None,
        priority=4,
    ),
    Rule(
        name="shop_now_cta",
        category=RuleCategory.CTA,
        condition="'shop' in str(features.get('cta', {}).get('text', '')).lower()",
        positive_output="shop now button, ecommerce CTA",
        negative_output=None,
        priority=4,
    ),
    Rule(
        name="learn_more_cta",
        category=RuleCategory.CTA,
        condition="'learn' in str(features.get('cta', {}).get('text', '')).lower()",
        positive_output="learn more button, informational CTA",
        negative_output=None,
        priority=4,
    ),
]

TYPOGRAPHY_RULES = [
    Rule(
        name="has_headline",
        category=RuleCategory.TYPOGRAPHY,
        condition="features.get('typography', {}).get('has_headline', False)",
        positive_output="prominent headline text, large typography",
        negative_output=None,
        priority=3,
    ),
    Rule(
        name="readable_text",
        category=RuleCategory.TYPOGRAPHY,
        condition="features.get('typography', {}).get('estimated_readability', 0) > 0.8",
        positive_output="clear readable text, good typography",
        negative_output="illegible text, poor readability",
        priority=3,
    ),
]

QUALITY_RULES = [
    Rule(
        name="high_quality",
        category=RuleCategory.QUALITY,
        condition="features.get('quality_score', 0.5) > 0.8",
        positive_output="high quality, professional, sharp details",
        negative_output="low quality, amateur",
        priority=1,
    ),
    Rule(
        name="sharp_image",
        category=RuleCategory.QUALITY,
        condition="features.get('sharpness_score', 0.5) > 0.8",
        positive_output="sharp focus, crisp details",
        negative_output="blurry, out of focus",
        priority=1,
    ),
]


# Industry-specific rule sets
INDUSTRY_RULES = {
    "finance": [
        Rule(
            name="finance_tone",
            category=RuleCategory.INDUSTRY,
            condition="True",
            positive_output="professional, trustworthy, corporate, financial services aesthetic",
            negative_output="casual, playful, unprofessional",
            priority=20,
        ),
        Rule(
            name="finance_elements",
            category=RuleCategory.INDUSTRY,
            condition="True",
            positive_output="clean graphs, confident people, modern office spaces, trust indicators",
            negative_output="cluttered, informal, cartoonish",
            priority=20,
        ),
    ],
    "ecommerce": [
        Rule(
            name="ecommerce_tone",
            category=RuleCategory.INDUSTRY,
            condition="True",
            positive_output="vibrant, enticing, action-oriented, shopping aesthetic",
            negative_output="dull, boring, static",
            priority=20,
        ),
        Rule(
            name="ecommerce_elements",
            category=RuleCategory.INDUSTRY,
            condition="True",
            positive_output="product showcase, lifestyle context, clear pricing, promotional feel",
            negative_output="no products, confusing layout",
            priority=20,
        ),
    ],
    "saas": [
        Rule(
            name="saas_tone",
            category=RuleCategory.INDUSTRY,
            condition="True",
            positive_output="modern, innovative, efficient, tech startup aesthetic",
            negative_output="outdated, traditional, generic",
            priority=20,
        ),
        Rule(
            name="saas_elements",
            category=RuleCategory.INDUSTRY,
            condition="True",
            positive_output="clean UI mockups, abstract tech elements, dashboard previews, gradients",
            negative_output="no interface elements, generic stock",
            priority=20,
        ),
    ],
    "healthcare": [
        Rule(
            name="healthcare_tone",
            category=RuleCategory.INDUSTRY,
            condition="True",
            positive_output="caring, professional, reassuring, medical aesthetic",
            negative_output="scary, alarming, graphic",
            priority=20,
        ),
        Rule(
            name="healthcare_elements",
            category=RuleCategory.INDUSTRY,
            condition="True",
            positive_output="medical professionals, clean environments, wellness imagery, calming colors",
            negative_output="graphic medical imagery, cold clinical",
            priority=20,
        ),
    ],
    "food_beverage": [
        Rule(
            name="food_tone",
            category=RuleCategory.INDUSTRY,
            condition="True",
            positive_output="appetizing, fresh, indulgent, culinary aesthetic",
            negative_output="unappetizing, cold, artificial",
            priority=20,
        ),
        Rule(
            name="food_elements",
            category=RuleCategory.INDUSTRY,
            condition="True",
            positive_output="close-up food shots, steam, texture details, warm tones, natural lighting",
            negative_output="artificial food, bad lighting, messy",
            priority=20,
        ),
    ],
    "technology": [
        Rule(
            name="tech_tone",
            category=RuleCategory.INDUSTRY,
            condition="True",
            positive_output="innovative, sleek, futuristic, tech aesthetic",
            negative_output="outdated, old-fashioned",
            priority=20,
        ),
        Rule(
            name="tech_elements",
            category=RuleCategory.INDUSTRY,
            condition="True",
            positive_output="devices, interfaces, abstract tech visuals, neon accents, dark themes",
            negative_output="no tech elements, generic imagery",
            priority=20,
        ),
    ],
}

# Base negative prompts (always included)
BASE_NEGATIVE_PROMPTS = [
    "blurry",
    "low quality", 
    "distorted",
    "watermark",
    "amateur",
    "poor composition",
    "bad lighting",
    "pixelated",
    "compressed artifacts",
]


# ============================================================================
# Rules Engine
# ============================================================================

class RulesEngine:
    """
    Deterministic rules engine for prompt generation.
    
    This engine applies a set of rules to extracted features
    to generate consistent, reproducible prompts.
    """
    
    def __init__(self):
        self.rules: List[Rule] = []
        self._load_default_rules()
    
    def _load_default_rules(self) -> None:
        """Load all default rule sets."""
        self.rules.extend(LAYOUT_RULES)
        self.rules.extend(COLOR_RULES)
        self.rules.extend(COMPOSITION_RULES)
        self.rules.extend(CTA_RULES)
        self.rules.extend(TYPOGRAPHY_RULES)
        self.rules.extend(QUALITY_RULES)
        
        # Sort by priority (higher first)
        self.rules.sort(key=lambda r: -r.priority)
    
    def add_rule(self, rule: Rule) -> None:
        """Add a custom rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: -r.priority)
    
    def generate(
        self,
        features: Dict[str, Any],
        industry: Optional[str] = None,
        include_negative: bool = True
    ) -> Dict[str, Any]:
        """
        Generate prompts from features using rules.
        
        Args:
            features: Extracted visual features
            industry: Industry classification
            include_negative: Whether to include negative prompt
            
        Returns:
            Dictionary with positive, negative prompts and metadata
        """
        positive_parts = []
        negative_parts = []
        matched_rules = []
        
        # Apply base rules
        for rule in self.rules:
            matches, positive, negative = rule.evaluate(features)
            if matches:
                if positive:
                    positive_parts.append(positive)
                if negative and include_negative:
                    negative_parts.append(negative)
                matched_rules.append(rule.name)
        
        # Apply industry-specific rules
        if industry and industry in INDUSTRY_RULES:
            for rule in INDUSTRY_RULES[industry]:
                matches, positive, negative = rule.evaluate(features)
                if matches:
                    if positive:
                        positive_parts.append(positive)
                    if negative and include_negative:
                        negative_parts.append(negative)
                    matched_rules.append(rule.name)
        
        # Add dominant colors if available
        colors = features.get("dominant_colors", [])
        if colors:
            if isinstance(colors[0], dict):
                color_names = [c.get("hex", "") for c in colors[:3] if c.get("hex")]
            else:
                color_names = [str(c) for c in colors[:3]]
            if color_names:
                positive_parts.append(f"color palette featuring {', '.join(color_names)}")
        
        # Add focal point
        focal_point = features.get("focal_point", "")
        if focal_point:
            positive_parts.append(f"focus on {focal_point}")
        
        # Add base negative prompts
        if include_negative:
            negative_parts.extend(BASE_NEGATIVE_PROMPTS)
        
        # Build final prompts
        positive_prompt = f"Advertisement creative: {', '.join(positive_parts)}"
        negative_prompt = ", ".join(set(negative_parts)) if negative_parts else ""
        
        return {
            "positive": positive_prompt,
            "negative": negative_prompt,
            "metadata": {
                "generation_method": "rules_engine",
                "industry": industry,
                "matched_rules": matched_rules,
                "rule_count": len(matched_rules),
                "confidence": min(0.9, 0.5 + len(matched_rules) * 0.05),
            }
        }
    
    def explain(self, features: Dict[str, Any], industry: Optional[str] = None) -> Dict[str, Any]:
        """
        Explain which rules matched and why.
        
        Useful for debugging and understanding prompt generation.
        """
        explanations = []
        
        for rule in self.rules:
            matches, positive, negative = rule.evaluate(features)
            explanations.append({
                "rule": rule.name,
                "category": rule.category.value,
                "condition": rule.condition,
                "matched": matches,
                "output": positive if matches else None,
            })
        
        if industry and industry in INDUSTRY_RULES:
            for rule in INDUSTRY_RULES[industry]:
                matches, positive, negative = rule.evaluate(features)
                explanations.append({
                    "rule": rule.name,
                    "category": "industry",
                    "condition": f"industry == '{industry}'",
                    "matched": matches,
                    "output": positive if matches else None,
                })
        
        return {
            "total_rules": len(explanations),
            "matched_rules": sum(1 for e in explanations if e["matched"]),
            "explanations": explanations,
        }

