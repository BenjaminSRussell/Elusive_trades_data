"""
Zero-shot Classification for part status detection.

This module uses transformer-based zero-shot classification to detect
part deprecation status and replacement information without training.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PartStatusClassifier:
    """
    Zero-shot classifier for detecting part status and relationships.

    Uses pre-trained transformer models to classify text without additional training.
    Detects:
    - Deprecation status (deprecated, discontinued, obsolete, etc.)
    - Replacement information (replaced by, superseded by, alternative, etc.)
    - Compatibility relationships (compatible with, equivalent to, etc.)
    """

    # Classification labels for deprecation status
    DEPRECATION_LABELS = [
        "discontinued",
        "deprecated",
        "obsolete",
        "no longer available",
        "end of life",
        "phased out"
    ]

    # Classification labels for replacement relationships
    REPLACEMENT_LABELS = [
        "replaced by",
        "superseded by",
        "supersedes",
        "alternative",
        "substitute",
        "updated to"
    ]

    # Classification labels for compatibility
    COMPATIBILITY_LABELS = [
        "compatible with",
        "equivalent to",
        "interchangeable with",
        "cross-reference",
        "same as"
    ]

    def __init__(self, model_name: str = "facebook/bart-large-mnli"):
        """
        Initialize the classifier.

        Args:
            model_name: HuggingFace model to use for zero-shot classification
                       Default: facebook/bart-large-mnli (good for zero-shot)
        """
        self.model_name = model_name
        self.pipeline = None

        logger.info(f"Initialized PartStatusClassifier with model: {model_name}")
        logger.info("Note: Model will be loaded on first use")

    def _load_pipeline(self):
        """Lazy-load the transformer pipeline."""
        if self.pipeline is None:
            try:
                from transformers import pipeline
                logger.info(f"Loading zero-shot classification pipeline: {self.model_name}")
                self.pipeline = pipeline(
                    "zero-shot-classification",
                    model=self.model_name,
                    device=-1  # Use CPU (-1) or GPU (0, 1, etc.)
                )
                logger.info("Pipeline loaded successfully")
            except ImportError:
                logger.error("transformers library not installed. Install with: pip install transformers torch")
                raise
            except Exception as e:
                logger.error(f"Error loading pipeline: {e}")
                raise

    def classify_deprecation_status(self, text: str, threshold: float = 0.5) -> Dict[str, Any]:
        """
        Classify if text indicates the part is deprecated.

        Args:
            text: Text to classify (product description, notes, etc.)
            threshold: Confidence threshold for positive classification

        Returns:
            Dictionary with classification results
        """
        self._load_pipeline()

        logger.info(f"Classifying deprecation status for text: {text[:100]}...")

        result = self.pipeline(
            text,
            candidate_labels=self.DEPRECATION_LABELS,
            multi_label=True
        )

        # Find labels above threshold
        deprecated_labels = []
        for label, score in zip(result['labels'], result['scores']):
            if score >= threshold:
                deprecated_labels.append({
                    "label": label,
                    "confidence": float(score)
                })

        is_deprecated = len(deprecated_labels) > 0

        return {
            "text": text,
            "is_deprecated": is_deprecated,
            "deprecation_indicators": deprecated_labels,
            "all_scores": {
                label: float(score)
                for label, score in zip(result['labels'], result['scores'])
            },
            "threshold": threshold,
            "timestamp": datetime.now().isoformat()
        }

    def classify_replacement_info(self, text: str, threshold: float = 0.5) -> Dict[str, Any]:
        """
        Classify if text contains replacement/supersession information.

        Args:
            text: Text to classify
            threshold: Confidence threshold for positive classification

        Returns:
            Dictionary with classification results
        """
        self._load_pipeline()

        logger.info(f"Classifying replacement info for text: {text[:100]}...")

        result = self.pipeline(
            text,
            candidate_labels=self.REPLACEMENT_LABELS,
            multi_label=True
        )

        # Find labels above threshold
        replacement_indicators = []
        for label, score in zip(result['labels'], result['scores']):
            if score >= threshold:
                replacement_indicators.append({
                    "label": label,
                    "confidence": float(score)
                })

        has_replacement_info = len(replacement_indicators) > 0

        return {
            "text": text,
            "has_replacement_info": has_replacement_info,
            "replacement_indicators": replacement_indicators,
            "all_scores": {
                label: float(score)
                for label, score in zip(result['labels'], result['scores'])
            },
            "threshold": threshold,
            "timestamp": datetime.now().isoformat()
        }

    def classify_compatibility(self, text: str, threshold: float = 0.5) -> Dict[str, Any]:
        """
        Classify if text contains compatibility/equivalency information.

        Args:
            text: Text to classify
            threshold: Confidence threshold for positive classification

        Returns:
            Dictionary with classification results
        """
        self._load_pipeline()

        logger.info(f"Classifying compatibility for text: {text[:100]}...")

        result = self.pipeline(
            text,
            candidate_labels=self.COMPATIBILITY_LABELS,
            multi_label=True
        )

        # Find labels above threshold
        compatibility_indicators = []
        for label, score in zip(result['labels'], result['scores']):
            if score >= threshold:
                compatibility_indicators.append({
                    "label": label,
                    "confidence": float(score)
                })

        has_compatibility_info = len(compatibility_indicators) > 0

        return {
            "text": text,
            "has_compatibility_info": has_compatibility_info,
            "compatibility_indicators": compatibility_indicators,
            "all_scores": {
                label: float(score)
                for label, score in zip(result['labels'], result['scores'])
            },
            "threshold": threshold,
            "timestamp": datetime.now().isoformat()
        }

    def classify_all(self, text: str, threshold: float = 0.5) -> Dict[str, Any]:
        """
        Run all classifications on the text.

        Args:
            text: Text to classify
            threshold: Confidence threshold for positive classification

        Returns:
            Dictionary with all classification results
        """
        logger.info(f"Running all classifications on text: {text[:100]}...")

        return {
            "text": text,
            "deprecation": self.classify_deprecation_status(text, threshold),
            "replacement": self.classify_replacement_info(text, threshold),
            "compatibility": self.classify_compatibility(text, threshold),
            "timestamp": datetime.now().isoformat()
        }

    def extract_part_numbers_from_text(self, text: str) -> List[str]:
        """
        Extract potential part numbers from text using regex patterns.

        Args:
            text: Text to extract part numbers from

        Returns:
            List of potential part numbers found
        """
        import re

        # Common part number patterns
        patterns = [
            r'\b[A-Z0-9]{6,15}\b',  # Alphanumeric 6-15 chars
            r'\b[A-Z]+\d+[A-Z]*\d*\b',  # Letters then numbers
            r'\b\d+[A-Z]+\d+\b',  # Numbers, letters, numbers
            r'\b[A-Z]\d{3,}[A-Z]*\d*\b'  # Single letter then digits
        ]

        part_numbers = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            part_numbers.update(matches)

        # Filter out common words that might match
        common_words = {'THE', 'AND', 'FOR', 'WITH', 'THIS', 'THAT', 'FROM', 'HAVE', 'BEEN'}
        part_numbers = [pn for pn in part_numbers if pn not in common_words]

        logger.info(f"Extracted {len(part_numbers)} potential part numbers from text")
        return list(part_numbers)


def main():
    """
    Example usage of the PartStatusClassifier.
    """
    print("\n" + "="*60)
    print("Zero-Shot Classification Examples")
    print("="*60)

    classifier = PartStatusClassifier()

    # Example 1: Deprecation detection
    print("\n--- Example 1: Deprecation Detection ---")
    text1 = "This capacitor has been discontinued and is no longer available from the manufacturer."
    result1 = classifier.classify_deprecation_status(text1)
    print(f"Text: {text1}")
    print(f"Is Deprecated: {result1['is_deprecated']}")
    print(f"Indicators: {result1['deprecation_indicators']}")

    # Example 2: Replacement detection
    print("\n--- Example 2: Replacement Detection ---")
    text2 = "Part 0131M00008P has been replaced by part CAP-440-4005. Please order the new part number."
    result2 = classifier.classify_replacement_info(text2)
    print(f"Text: {text2}")
    print(f"Has Replacement Info: {result2['has_replacement_info']}")
    print(f"Indicators: {result2['replacement_indicators']}")

    # Example 3: Compatibility detection
    print("\n--- Example 3: Compatibility Detection ---")
    text3 = "This capacitor is equivalent to Carrier P291-4053RS and Trane CAP050450440RU."
    result3 = classifier.classify_compatibility(text3)
    print(f"Text: {text3}")
    print(f"Has Compatibility Info: {result3['has_compatibility_info']}")
    print(f"Indicators: {result3['compatibility_indicators']}")

    # Example 4: Extract part numbers
    print("\n--- Example 4: Part Number Extraction ---")
    text4 = "Compatible parts include 0131M00008P, P291-4053RS, and CAP050450440RU."
    part_numbers = classifier.extract_part_numbers_from_text(text4)
    print(f"Text: {text4}")
    print(f"Extracted Part Numbers: {part_numbers}")

    # Example 5: Classify all at once
    print("\n--- Example 5: Full Classification ---")
    text5 = "Part B1340021 is obsolete. Use replacement part B1340021S instead. This new part is compatible with all previous models."
    result5 = classifier.classify_all(text5)
    print(f"Text: {text5}")
    print(f"Deprecated: {result5['deprecation']['is_deprecated']}")
    print(f"Has Replacement: {result5['replacement']['has_replacement_info']}")
    print(f"Has Compatibility: {result5['compatibility']['has_compatibility_info']}")


if __name__ == "__main__":
    main()
