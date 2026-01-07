"""
LLM Interface

Defines the contract for language model operations (reverse-prompt generation).
Implementations: 
- LocalLLM: Template-based or Ollama for local development
- VertexLLM: Vertex AI for cloud (CLOUD MODE ONLY)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PromptStyle(Enum):
    """Prompt generation styles."""
    DESCRIPTIVE = "descriptive"      # Detailed description
    TECHNICAL = "technical"          # Technical photography terms
    ARTISTIC = "artistic"            # Artistic/creative language
    MINIMAL = "minimal"              # Concise, essential elements only
    STRUCTURED = "structured"        # Structured format with sections


@dataclass
class PromptResult:
    """Result of prompt generation."""
    positive: str
    negative: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    generation_method: str = "unknown"
    model: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "positive": self.positive,
            "negative": self.negative,
            "metadata": self.metadata,
            "confidence": self.confidence,
            "generation_method": self.generation_method,
            "model": self.model,
        }


class LLMInterface(ABC):
    """
    Abstract interface for LLM operations (reverse-prompt generation).
    
    Implementations:
    - LocalLLM: Template-based or Ollama (local mode)
    - VertexLLM: Vertex AI Gemini (cloud mode ONLY - NOT available locally)
    
    CRITICAL: Vertex AI MUST ONLY exist in cloud mode.
    In local mode, use LocalLLM with templates or Ollama.
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the LLM client."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close LLM connections."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if LLM is healthy and accessible."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this LLM adapter is available in the current mode."""
        pass
    
    @abstractmethod
    async def generate_prompt(
        self,
        features: Dict[str, Any],
        industry: Optional[str] = None,
        style: PromptStyle = PromptStyle.DESCRIPTIVE,
        include_negative: bool = True
    ) -> PromptResult:
        """
        Generate reverse prompts from extracted features.
        
        Args:
            features: Extracted visual features dictionary
            industry: Industry classification
            style: Prompt generation style
            include_negative: Whether to generate negative prompts
            
        Returns:
            PromptResult with positive prompt, negative prompt, and metadata
        """
        pass
    
    @abstractmethod
    async def generate_batch(
        self,
        items: List[Dict[str, Any]],
        concurrency: int = 5
    ) -> List[PromptResult]:
        """
        Generate prompts for multiple items in parallel.
        
        Args:
            items: List of dicts with 'features' and optional 'industry'
            concurrency: Maximum concurrent generations
            
        Returns:
            List of PromptResults
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_style_presets(self) -> Dict[str, Dict[str, str]]:
        """Get available style presets for prompt enhancement."""
        pass


class VertexAINotAvailableError(Exception):
    """
    Raised when Vertex AI is called in local mode.
    
    Vertex AI is CLOUD MODE ONLY. This error ensures that
    local development never accidentally uses cloud resources.
    """
    
    def __init__(self, message: str = None):
        self.message = message or (
            "Vertex AI is not available in local mode. "
            "Use MODE=cloud for Vertex AI access, or use LocalLLM with templates/Ollama."
        )
        super().__init__(self.message)

