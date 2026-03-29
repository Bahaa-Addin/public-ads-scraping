"""
Local LLM Adapter

Implements LLMInterface using:
1. Template-based deterministic prompt generation (default)
2. Optional Ollama integration for local AI inference

CRITICAL: This adapter does NOT use Vertex AI.
Vertex AI is CLOUD MODE ONLY.

Template-based generation is deterministic and reproducible,
making it ideal for testing and development.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from agent.interfaces.llm import (
    LLMInterface,
    PromptResult,
    PromptStyle,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Industry-specific prompt templates
# ============================================================================

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

LAYOUT_PROMPT_COMPONENTS = {
    "hero": "large hero image composition, prominent central subject, text overlay area",
    "grid": "multi-panel grid layout, organized sections, visual hierarchy",
    "split": "split screen composition, dual focus areas, balanced design",
    "minimal": "minimalist design, ample white space, focused subject",
    "product_focus": "product-centered composition, clean background, detail visibility",
    "lifestyle": "lifestyle context, environmental setting, natural staging",
    "text_heavy": "text-forward design, readable typography, information hierarchy"
}


class LocalLLM(LLMInterface):
    """
    Local LLM implementation using templates and optional Ollama.
    
    DOES NOT use Vertex AI - Vertex is cloud-only.
    
    Modes:
    1. template: Deterministic template-based generation (default)
    2. ollama: Uses local Ollama instance for AI inference
    """
    
    def __init__(
        self,
        mode: str = "template",  # "template" or "ollama"
        ollama_host: str = "http://localhost:11434",
        ollama_model: str = "llama2",
    ):
        self.mode = mode
        self.ollama_host = ollama_host
        self.ollama_model = ollama_model
        self._ollama_available = False
        
    async def initialize(self) -> None:
        """Initialize the LLM adapter."""
        if self.mode == "ollama":
            self._ollama_available = await self._check_ollama()
            if self._ollama_available:
                logger.info(f"Ollama available at {self.ollama_host} with model {self.ollama_model}")
            else:
                logger.warning("Ollama not available, falling back to template mode")
                self.mode = "template"
        
        logger.info(f"LocalLLM initialized in {self.mode} mode")
    
    async def close(self) -> None:
        """Close LLM connections."""
        logger.info("LocalLLM closed")
    
    async def health_check(self) -> bool:
        """Check if LLM is healthy."""
        if self.mode == "ollama":
            return await self._check_ollama()
        return True  # Template mode is always healthy
    
    def is_available(self) -> bool:
        """Check if this LLM adapter is available (always true for local)."""
        return True
    
    async def _check_ollama(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_host}/api/tags", timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m.get("name", "") for m in data.get("models", [])]
                        return any(self.ollama_model in m for m in models)
        except Exception:
            pass
        return False
    
    async def generate_prompt(
        self,
        features: Dict[str, Any],
        industry: Optional[str] = None,
        style: PromptStyle = PromptStyle.DESCRIPTIVE,
        include_negative: bool = True
    ) -> PromptResult:
        """Generate reverse prompts from extracted features."""
        logger.info(f"Generating prompt in {self.mode} mode for industry: {industry}")
        
        if self.mode == "ollama" and self._ollama_available:
            return await self._generate_with_ollama(features, industry, style, include_negative)
        
        return self._generate_from_template(features, industry, style, include_negative)
    
    async def _generate_with_ollama(
        self,
        features: Dict[str, Any],
        industry: Optional[str],
        style: PromptStyle,
        include_negative: bool
    ) -> PromptResult:
        """Generate prompts using local Ollama."""
        try:
            import aiohttp
            import json
            
            # Build prompt for Ollama
            system_prompt = self._build_system_prompt(style)
            user_prompt = self._build_user_prompt(features, industry, include_negative)
            
            payload = {
                "model": self.ollama_model,
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 512,
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_host}/api/generate",
                    json=payload,
                    timeout=60
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        response_text = data.get("response", "")
                        return self._parse_llm_response(response_text, include_negative, "ollama")
            
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}, falling back to template")
        
        return self._generate_from_template(features, industry, style, include_negative)
    
    def _generate_from_template(
        self,
        features: Dict[str, Any],
        industry: Optional[str],
        style: PromptStyle,
        include_negative: bool
    ) -> PromptResult:
        """Generate prompts using deterministic templates."""
        # Build positive prompt components
        components = []
        
        # Layout description
        layout = features.get("layout_type", "minimal")
        if layout in LAYOUT_PROMPT_COMPONENTS:
            components.append(LAYOUT_PROMPT_COMPONENTS[layout])
        
        # Color description
        colors = features.get("dominant_colors", [])
        if colors:
            if isinstance(colors[0], dict):
                color_names = [c.get("hex", "#000000") for c in colors[:3]]
            else:
                color_names = colors[:3]
            components.append(f"color palette featuring {', '.join(str(c) for c in color_names)}")
        
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
        if isinstance(typography, dict):
            if typography.get("has_headline"):
                components.append("prominent headline text")
        
        # CTA
        cta = features.get("cta", {})
        if isinstance(cta, dict) and cta.get("detected"):
            cta_text = cta.get("text", "call to action")
            components.append(f"clear CTA button: '{cta_text}'")
        
        # Composition
        composition = features.get("composition", {})
        if isinstance(composition, dict):
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
            if industry_mods.get("tone"):
                components.append(industry_mods["tone"])
            if industry_mods.get("elements"):
                components.append(industry_mods["elements"])
        
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
        
        return PromptResult(
            positive=positive_prompt,
            negative=negative_prompt,
            metadata={
                "industry": industry,
                "style": style.value,
                "feature_count": len(components),
            },
            confidence=0.75,
            generation_method="template",
            model=None
        )
    
    def _build_system_prompt(self, style: PromptStyle) -> str:
        """Build the system prompt for LLM generation."""
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
        import json
        
        prompt = f"""Generate a reverse-prompt for an advertisement creative with these features:

**Visual Features:**
{json.dumps(features, indent=2, default=str)}

**Industry:** {industry or 'general'}

Please generate:
1. A POSITIVE prompt that describes what the image should contain
2. {"A NEGATIVE prompt that describes what to avoid" if include_negative else ""}

Format your response as:
POSITIVE: [your positive prompt here]
{"NEGATIVE: [your negative prompt here]" if include_negative else ""}"""

        return prompt
    
    def _parse_llm_response(
        self,
        response_text: str,
        include_negative: bool,
        method: str
    ) -> PromptResult:
        """Parse the LLM response into structured output."""
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
        
        return PromptResult(
            positive=positive,
            negative=negative,
            metadata={
                "raw_response_length": len(response_text),
            },
            confidence=0.85,
            generation_method=method,
            model=self.ollama_model if method == "ollama" else None
        )
    
    async def generate_batch(
        self,
        items: List[Dict[str, Any]],
        concurrency: int = 5
    ) -> List[PromptResult]:
        """Generate prompts for multiple items."""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def generate_one(item):
            async with semaphore:
                return await self.generate_prompt(
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
        """Enhance an existing prompt with additional modifiers."""
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

