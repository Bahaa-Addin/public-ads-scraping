"""
Reverse Prompt Generation using Vertex AI

Converts structured visual features and industry classification
into natural language prompts suitable for AI image generation.

Supports:
- Positive prompts (what to include)
- Negative prompts (what to avoid)
- Style-specific prompts
- Industry-tailored language
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Types and Templates
# ============================================================================

class PromptStyle(Enum):
    """Prompt generation styles."""
    DESCRIPTIVE = "descriptive"      # Detailed description
    TECHNICAL = "technical"          # Technical photography terms
    ARTISTIC = "artistic"            # Artistic/creative language
    MINIMAL = "minimal"              # Concise, essential elements only
    STRUCTURED = "structured"        # Structured format with sections


@dataclass
class PromptTemplate:
    """Template for generating prompts."""
    name: str
    positive_template: str
    negative_template: str
    style_modifiers: Dict[str, str] = field(default_factory=dict)
    industry_modifiers: Dict[str, str] = field(default_factory=dict)


# Industry-specific prompt enhancements
INDUSTRY_PROMPT_MODIFIERS = {
    "finance": {
        "tone": "professional, trustworthy, corporate",
        "elements": "clean graphs, confident people, modern office spaces",
        "colors": "blues, greens, white, gold accents",
        "avoid": "clutter, informal imagery, bright saturated colors"
    },
    "ecommerce": {
        "tone": "vibrant, enticing, action-oriented",
        "elements": "product showcase, lifestyle context, clear pricing",
        "colors": "brand colors, high contrast CTAs, white backgrounds",
        "avoid": "dull colors, complex backgrounds, small text"
    },
    "saas": {
        "tone": "modern, innovative, efficient",
        "elements": "clean UI mockups, abstract tech elements, dashboard previews",
        "colors": "gradients, purples, blues, dark mode aesthetics",
        "avoid": "outdated interfaces, cluttered screens, generic stock photos"
    },
    "healthcare": {
        "tone": "caring, professional, reassuring",
        "elements": "medical professionals, clean environments, wellness imagery",
        "colors": "soft blues, greens, white, calming tones",
        "avoid": "graphic medical imagery, cold clinical looks, red warnings"
    },
    "education": {
        "tone": "inspiring, accessible, growth-oriented",
        "elements": "students, books, digital learning, achievements",
        "colors": "warm tones, academic colors, inviting palettes",
        "avoid": "boring classroom imagery, dated technology"
    },
    "entertainment": {
        "tone": "exciting, fun, engaging",
        "elements": "dynamic scenes, characters, action shots",
        "colors": "bold, saturated, high contrast",
        "avoid": "static imagery, muted tones, corporate feel"
    },
    "food_beverage": {
        "tone": "appetizing, fresh, indulgent",
        "elements": "close-up food shots, steam, texture details",
        "colors": "warm tones, natural colors, appetizing presentation",
        "avoid": "artificial looking food, cold lighting, messy presentation"
    },
    "travel": {
        "tone": "adventurous, aspirational, relaxing",
        "elements": "scenic destinations, happy travelers, luxury amenities",
        "colors": "natural landscapes, sunset tones, ocean blues",
        "avoid": "crowded tourist spots, generic hotel rooms"
    },
    "automotive": {
        "tone": "powerful, sleek, aspirational",
        "elements": "vehicle exterior/interior, motion blur, scenic roads",
        "colors": "metallic finishes, dramatic lighting, bold colors",
        "avoid": "static parked cars, dirty vehicles, cluttered backgrounds"
    },
    "real_estate": {
        "tone": "welcoming, spacious, aspirational",
        "elements": "interior/exterior shots, natural light, staging",
        "colors": "neutral tones, natural wood, bright spaces",
        "avoid": "cluttered rooms, poor lighting, dated decor"
    },
    "fashion": {
        "tone": "stylish, confident, trendy",
        "elements": "models, outfit details, lifestyle context",
        "colors": "seasonal palettes, brand colors, editorial lighting",
        "avoid": "wrinkled clothes, poor fit, dated styles"
    },
    "technology": {
        "tone": "innovative, sleek, futuristic",
        "elements": "devices, interfaces, abstract tech visuals",
        "colors": "dark themes, neon accents, clean gradients",
        "avoid": "outdated technology, cluttered setups, generic stock"
    }
}


# Layout-specific prompt components
LAYOUT_PROMPT_COMPONENTS = {
    "hero": "large hero image composition, prominent central subject, text overlay area",
    "grid": "multi-panel grid layout, organized sections, visual hierarchy",
    "split": "split screen composition, dual focus areas, balanced design",
    "minimal": "minimalist design, ample white space, focused subject",
    "product_focus": "product-centered composition, clean background, detail visibility",
    "lifestyle": "lifestyle context, environmental setting, natural staging",
    "text_heavy": "text-forward design, readable typography, information hierarchy"
}


# ============================================================================
# Prompt Generator
# ============================================================================

class ReversePromptGenerator:
    """
    Generates reverse prompts from extracted features using Vertex AI.
    
    The generator can work in two modes:
    1. Template-based: Uses structured templates with feature interpolation
    2. AI-generated: Uses Vertex AI (Gemini) for natural language generation
    """
    
    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "gemini-1.5-pro",
        use_ai_generation: bool = True
    ):
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.use_ai_generation = use_ai_generation
        self._client = None
        
    async def _ensure_client(self) -> None:
        """Initialize Vertex AI client if needed."""
        if self._client is not None:
            return
            
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            
            vertexai.init(project=self.project_id, location=self.location)
            self._client = GenerativeModel(self.model_name)
            logger.info(f"Initialized Vertex AI client: {self.model_name}")
            
        except ImportError:
            logger.warning("vertexai package not installed, using template-based generation")
            self.use_ai_generation = False
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            self.use_ai_generation = False
    
    async def generate(
        self,
        features: Dict[str, Any],
        industry: Optional[str] = None,
        style: PromptStyle = PromptStyle.DESCRIPTIVE,
        include_negative: bool = True
    ) -> Dict[str, Any]:
        """
        Generate reverse prompts from extracted features.
        
        Args:
            features: Extracted visual features dictionary
            industry: Industry classification
            style: Prompt generation style
            include_negative: Whether to generate negative prompts
            
        Returns:
            Dictionary with positive prompt, negative prompt, and metadata
        """
        logger.info(f"Generating reverse prompt for industry: {industry}")
        
        if self.use_ai_generation:
            await self._ensure_client()
            if self._client:
                return await self._generate_with_ai(features, industry, style, include_negative)
        
        return self._generate_from_template(features, industry, style, include_negative)
    
    async def _generate_with_ai(
        self,
        features: Dict[str, Any],
        industry: Optional[str],
        style: PromptStyle,
        include_negative: bool
    ) -> Dict[str, Any]:
        """Generate prompts using Vertex AI Gemini."""
        try:
            from vertexai.generative_models import GenerationConfig
            
            # Build the prompt for Gemini
            system_prompt = self._build_system_prompt(style)
            user_prompt = self._build_user_prompt(features, industry, include_negative)
            
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # Generate response
            generation_config = GenerationConfig(
                temperature=0.7,
                max_output_tokens=1024,
                top_p=0.9,
            )
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.generate_content(
                    full_prompt,
                    generation_config=generation_config
                )
            )
            
            # Parse response
            result = self._parse_ai_response(response.text, include_negative)
            result["metadata"]["generation_method"] = "vertex_ai"
            result["metadata"]["model"] = self.model_name
            
            return result
            
        except Exception as e:
            logger.error(f"AI generation failed: {e}, falling back to template")
            return self._generate_from_template(features, industry, style, include_negative)
    
    def _generate_from_template(
        self,
        features: Dict[str, Any],
        industry: Optional[str],
        style: PromptStyle,
        include_negative: bool
    ) -> Dict[str, Any]:
        """Generate prompts using structured templates."""
        # Build positive prompt components
        components = []
        
        # Layout description
        layout = features.get("layout_type", "minimal")
        if layout in LAYOUT_PROMPT_COMPONENTS:
            components.append(LAYOUT_PROMPT_COMPONENTS[layout])
        
        # Color description
        colors = features.get("dominant_colors", [])
        if colors:
            color_names = [c.get("hex", "#000000") for c in colors[:3]]
            components.append(f"color palette featuring {', '.join(color_names)}")
        
        # Brightness and contrast
        brightness = features.get("overall_brightness", 0.5)
        if brightness > 0.7:
            components.append("bright, well-lit")
        elif brightness < 0.3:
            components.append("dark, moody lighting")
        
        contrast = features.get("contrast_level", 0.5)
        if contrast > 0.7:
            components.append("high contrast")
        
        # Focal point
        focal_point = features.get("focal_point", "product")
        components.append(f"focus on {focal_point}")
        
        # Typography
        typography = features.get("typography", {})
        if typography.get("has_headline"):
            components.append("prominent headline text")
        
        # CTA
        cta = features.get("cta", {})
        if cta.get("detected"):
            cta_text = cta.get("text", "call to action")
            components.append(f"clear CTA button: '{cta_text}'")
        
        # Composition
        composition = features.get("composition", {})
        if composition.get("rule_of_thirds", 0) > 0.7:
            components.append("rule of thirds composition")
        if composition.get("symmetry", 0) > 0.7:
            components.append("symmetrical layout")
        
        # Quality
        quality = features.get("quality_score", 0.8)
        if quality > 0.8:
            components.append("high quality, professional")
        
        # Industry-specific modifiers
        industry_mods = INDUSTRY_PROMPT_MODIFIERS.get(industry or "other", {})
        if industry_mods:
            components.append(industry_mods.get("tone", ""))
            components.append(industry_mods.get("elements", ""))
        
        # Build positive prompt
        positive_prompt = ", ".join(filter(None, components))
        positive_prompt = f"Advertisement creative: {positive_prompt}"
        
        # Build negative prompt
        negative_prompt = ""
        if include_negative:
            negative_components = [
                "blurry", "low quality", "distorted", "watermark",
                "amateur", "cluttered", "poor composition"
            ]
            
            if industry_mods.get("avoid"):
                negative_components.append(industry_mods["avoid"])
            
            negative_prompt = ", ".join(negative_components)
        
        return {
            "positive": positive_prompt,
            "negative": negative_prompt,
            "metadata": {
                "generation_method": "template",
                "industry": industry,
                "style": style.value,
                "feature_count": len(components),
                "confidence": 0.75
            }
        }
    
    def _build_system_prompt(self, style: PromptStyle) -> str:
        """Build the system prompt for AI generation."""
        base = """You are an expert at analyzing visual advertisement creatives and generating 
prompts that could reproduce similar designs using AI image generation tools.

Your task is to convert structured visual features into natural language prompts 
that capture the essence of the original creative while being suitable for 
text-to-image AI models like Midjourney, DALL-E, or Stable Diffusion.

Guidelines:
- Be specific about composition, colors, and layout
- Include relevant style keywords
- Mention lighting and mood
- Reference photography or design techniques when applicable
- Keep prompts concise but comprehensive
- Use comma-separated descriptive phrases"""

        style_additions = {
            PromptStyle.DESCRIPTIVE: "\n\nUse rich, descriptive language with detailed visual descriptions.",
            PromptStyle.TECHNICAL: "\n\nUse technical photography and design terminology.",
            PromptStyle.ARTISTIC: "\n\nUse artistic and creative language, reference art movements and styles.",
            PromptStyle.MINIMAL: "\n\nBe concise. Focus only on essential elements.",
            PromptStyle.STRUCTURED: "\n\nOrganize the prompt into clear sections: Subject, Style, Composition, Colors, Mood."
        }
        
        return base + style_additions.get(style, "")
    
    def _build_user_prompt(
        self,
        features: Dict[str, Any],
        industry: Optional[str],
        include_negative: bool
    ) -> str:
        """Build the user prompt with feature data."""
        prompt = f"""Generate a reverse-prompt for an advertisement creative with these features:

**Visual Features:**
{json.dumps(features, indent=2)}

**Industry:** {industry or 'general'}

Please generate:
1. A POSITIVE prompt that describes what the image should contain
2. {"A NEGATIVE prompt that describes what to avoid" if include_negative else ""}

Format your response as:
POSITIVE: [your positive prompt here]
{"NEGATIVE: [your negative prompt here]" if include_negative else ""}"""

        return prompt
    
    def _parse_ai_response(
        self,
        response_text: str,
        include_negative: bool
    ) -> Dict[str, Any]:
        """Parse the AI response into structured output."""
        positive = ""
        negative = ""
        
        lines = response_text.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            if line.upper().startswith("POSITIVE:"):
                positive = line[9:].strip()
            elif line.upper().startswith("NEGATIVE:") and include_negative:
                negative = line[9:].strip()
        
        # Fallback if parsing fails
        if not positive:
            positive = response_text.strip()
        
        return {
            "positive": positive,
            "negative": negative,
            "metadata": {
                "raw_response_length": len(response_text),
                "confidence": 0.85
            }
        }
    
    async def generate_batch(
        self,
        items: List[Dict[str, Any]],
        concurrency: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate prompts for multiple items in parallel.
        
        Args:
            items: List of dicts with 'features' and optional 'industry'
            concurrency: Maximum concurrent generations
            
        Returns:
            List of prompt results
        """
        semaphore = asyncio.Semaphore(concurrency)
        
        async def generate_one(item):
            async with semaphore:
                return await self.generate(
                    features=item.get("features", {}),
                    industry=item.get("industry")
                )
        
        tasks = [generate_one(item) for item in items]
        return await asyncio.gather(*tasks)
    
    def enhance_prompt(
        self,
        base_prompt: str,
        enhancements: Dict[str, Any]
    ) -> str:
        """
        Enhance an existing prompt with additional modifiers.
        
        Args:
            base_prompt: The base prompt to enhance
            enhancements: Dictionary of enhancements to add
            
        Returns:
            Enhanced prompt string
        """
        parts = [base_prompt]
        
        if enhancements.get("quality"):
            parts.append("high quality, 4k, detailed")
        
        if enhancements.get("style"):
            parts.append(f"in the style of {enhancements['style']}")
        
        if enhancements.get("lighting"):
            parts.append(f"{enhancements['lighting']} lighting")
        
        if enhancements.get("camera"):
            parts.append(f"shot with {enhancements['camera']}")
        
        if enhancements.get("aspect_ratio"):
            parts.append(f"--ar {enhancements['aspect_ratio']}")
        
        return ", ".join(parts)
    
    def get_style_presets(self) -> Dict[str, Dict[str, str]]:
        """Get available style presets for prompt enhancement."""
        return {
            "photorealistic": {
                "suffix": "photorealistic, 8k uhd, dslr, high quality",
                "negative": "illustration, cartoon, drawing, art"
            },
            "digital_art": {
                "suffix": "digital art, trending on artstation, highly detailed",
                "negative": "photo, photograph, realistic"
            },
            "minimalist": {
                "suffix": "minimalist design, clean, simple, elegant",
                "negative": "cluttered, busy, complex, detailed"
            },
            "corporate": {
                "suffix": "professional, corporate, business, polished",
                "negative": "casual, informal, playful, quirky"
            },
            "vibrant": {
                "suffix": "vibrant colors, bold, eye-catching, dynamic",
                "negative": "muted, dull, desaturated, bland"
            }
        }

