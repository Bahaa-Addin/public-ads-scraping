"""
Feature Extraction Module

Provides ML-ready feature extraction for creative ad assets,
including layout analysis, color extraction, typography detection,
and CTA recognition.
"""

from .extract_features import (
    FeatureExtractor,
    IndustryClassifier,
    LayoutType,
    FocalPoint,
    VisualComplexity
)

__all__ = [
    'FeatureExtractor',
    'IndustryClassifier',
    'LayoutType',
    'FocalPoint',
    'VisualComplexity'
]

