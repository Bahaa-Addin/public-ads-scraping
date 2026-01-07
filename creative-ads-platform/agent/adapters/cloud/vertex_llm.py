"""
Vertex AI LLM Adapter

Implements LLMInterface using Google Cloud Vertex AI.

╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║  ██████╗██╗      ██████╗ ██╗   ██╗██████╗     ███╗   ███╗ ██████╗ ██████╗ ███████╗  ║
║ ██╔════╝██║     ██╔═══██╗██║   ██║██╔══██╗    ████╗ ████║██╔═══██╗██╔══██╗██╔════╝  ║
║ ██║     ██║     ██║   ██║██║   ██║██║  ██║    ██╔████╔██║██║   ██║██║  ██║█████╗    ║
║ ██║     ██║     ██║   ██║██║   ██║██║  ██║    ██║╚██╔╝██║██║   ██║██║  ██║██╔══╝    ║
║ ╚██████╗███████╗╚██████╔╝╚██████╔╝██████╔╝    ██║ ╚═╝ ██║╚██████╔╝██████╔╝███████╗  ║
║  ╚═════╝╚══════╝ ╚═════╝  ╚═════╝ ╚═════╝     ╚═╝     ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝  ║
║                                                                              ║
║  THIS ADAPTER IS CLOUD MODE ONLY!                                           ║
║                                                                              ║
║  Vertex AI MUST ONLY exist in cloud mode. There is NO local fallback.       ║
║  In local mode, use LocalLLM with templates or Ollama.                      ║
║                                                                              ║
║  Attempting to use this adapter in local mode will raise:                    ║
║  VertexAINotAvailableError                                                   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from agent.interfaces.llm import (
    LLMInterface,
    PromptResult,
    PromptStyle,
    VertexAINotAvailableError,
)

logger = logging.getLogger(__name__)


class VertexLLM(LLMInterface):
    """
    Vertex AI LLM implementation using Gemini models.
    
    CLOUD MODE ONLY!
    
    This adapter will HARD FAIL if MODE != "cloud".
    There is no local fallback - use LocalLLM for local development.
    """
    
    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "gemini-1.5-pro",
    ):
        # CRITICAL: Validate mode IMMEDIATELY
        self._validate_mode()
        
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self._client = None
        self._initialized = False
        
    def _validate_mode(self) -> None:
        """
        Validate that we're in cloud mode.
        
        CRITICAL: This MUST be called in __init__ to prevent any
        possibility of Vertex AI being used in local mode.
        """
        mode = os.environ.get("MODE", "local").lower()
        
        if mode != "cloud":
            raise VertexAINotAvailableError(
                f"Vertex AI is NOT available in {mode} mode. "
                f"Vertex AI can ONLY be used when MODE=cloud. "
                f"For local development, use LocalLLM with templates or Ollama. "
                f"Set MODE=cloud to use Vertex AI."
            )
    
    async def initialize(self) -> None:
        """Initialize Vertex AI client."""
        # Double-check mode (paranoid safety)
        self._validate_mode()
        
        import vertexai
        from vertexai.generative_models import GenerativeModel
        
        vertexai.init(project=self.project_id, location=self.location)
        self._client = GenerativeModel(self.model_name)
        self._initialized = True
        
        logger.info(f"Initialized Vertex AI client: {self.model_name} at {self.location}")
    
    async def close(self) -> None:
        """Close Vertex AI connections."""
        self._client = None
        self._initialized = False
        logger.info("Vertex AI client closed")
    
    async def health_check(self) -> bool:
        """Check if Vertex AI is healthy and accessible."""
        self._validate_mode()  # Always validate
        
        try:
            if not self._initialized:
                return False
            
            # Try a simple generation to verify connectivity
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.generate_content("Hello")
            )
            return response is not None
            
        except Exception as e:
            logger.error(f"Vertex AI health check failed: {e}")
            return False
    
    def is_available(self) -> bool:
        """
        Check if this LLM adapter is available.
        
        Returns False if MODE != cloud.
        """
        mode = os.environ.get("MODE", "local").lower()
        return mode == "cloud" and self._initialized
    
    async def generate_prompt(
        self,
        features: Dict[str, Any],
        industry: Optional[str] = None,
        style: PromptStyle = PromptStyle.DESCRIPTIVE,
        include_negative: bool = True
    ) -> PromptResult:
        """Generate reverse prompts using Vertex AI Gemini."""
        # ALWAYS validate mode before any operation
        self._validate_mode()
        
        if not self._initialized:
            await self.initialize()
        
        logger.info(f"Generating prompt with Vertex AI for industry: {industry}")
        
        from vertexai.generative_models import GenerationConfig
        
        # Build prompts
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
        return self._parse_response(response.text, include_negative, industry, style)
    
    def _build_system_prompt(self, style: PromptStyle) -> str:
        """Build the system prompt for Vertex AI."""
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
{json.dumps(features, indent=2, default=str)}

**Industry:** {industry or 'general'}

Please generate:
1. A POSITIVE prompt that describes what the image should contain
2. {"A NEGATIVE prompt that describes what to avoid" if include_negative else ""}

Format your response as:
POSITIVE: [your positive prompt here]
{"NEGATIVE: [your negative prompt here]" if include_negative else ""}"""

        return prompt
    
    def _parse_response(
        self,
        response_text: str,
        include_negative: bool,
        industry: Optional[str],
        style: PromptStyle
    ) -> PromptResult:
        """Parse Vertex AI response into structured output."""
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
                "industry": industry,
                "style": style.value,
                "raw_response_length": len(response_text),
            },
            confidence=0.90,  # Higher confidence for AI-generated
            generation_method="vertex_ai",
            model=self.model_name
        )
    
    async def generate_batch(
        self,
        items: List[Dict[str, Any]],
        concurrency: int = 5
    ) -> List[PromptResult]:
        """Generate prompts for multiple items in parallel."""
        # ALWAYS validate mode
        self._validate_mode()
        
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

