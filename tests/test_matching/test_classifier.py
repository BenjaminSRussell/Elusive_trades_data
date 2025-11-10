"""
TDD Tests for PartStatusClassifier.
"""

import unittest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phase2_matching.classifier import PartStatusClassifier


class TestPartStatusClassifier(unittest.TestCase):
    """Test cases for PartStatusClassifier."""

    def setUp(self):
        """Set up test fixtures."""
        self.classifier = PartStatusClassifier()

    def test_initialization(self):
        """Test classifier initialization."""
        self.assertIsNotNone(self.classifier)
        self.assertIsNotNone(self.classifier.model_name)

    def test_deprecation_labels_defined(self):
        """Test that deprecation labels are defined."""
        self.assertGreater(len(PartStatusClassifier.DEPRECATION_LABELS), 0)
        self.assertIn("discontinued", PartStatusClassifier.DEPRECATION_LABELS)

    def test_replacement_labels_defined(self):
        """Test that replacement labels are defined."""
        self.assertGreater(len(PartStatusClassifier.REPLACEMENT_LABELS), 0)
        self.assertIn("replaced by", PartStatusClassifier.REPLACEMENT_LABELS)

    def test_compatibility_labels_defined(self):
        """Test that compatibility labels are defined."""
        self.assertGreater(len(PartStatusClassifier.COMPATIBILITY_LABELS), 0)
        self.assertIn("compatible with", PartStatusClassifier.COMPATIBILITY_LABELS)

    def test_extract_part_numbers_basic(self):
        """Test extracting part numbers from text."""
        text = "Part number 0131M00008P is compatible with P291-4053RS"
        part_numbers = self.classifier.extract_part_numbers_from_text(text)

        self.assertIsInstance(part_numbers, list)
        self.assertGreater(len(part_numbers), 0)

    def test_extract_part_numbers_alphanumeric(self):
        """Test extracting alphanumeric part numbers."""
        text = "Compatible parts: ABC123, XYZ789, TEST12345"
        part_numbers = self.classifier.extract_part_numbers_from_text(text)

        self.assertGreater(len(part_numbers), 0)

    def test_extract_part_numbers_filters_common_words(self):
        """Test that common words are filtered out."""
        text = "THE PART AND FOR WITH"
        part_numbers = self.classifier.extract_part_numbers_from_text(text)

        # Common words should be filtered
        for pn in part_numbers:
            self.assertNotIn(pn, ['THE', 'AND', 'FOR', 'WITH'])

    def test_extract_part_numbers_various_formats(self):
        """Test extracting various part number formats."""
        test_cases = [
            ("Part 0131M00008P", True),
            ("Model B1340021S", True),
            ("Part P291-4053RS", True),
            ("Code CAP050450440RU", True)
        ]

        for text, should_find in test_cases:
            part_numbers = self.classifier.extract_part_numbers_from_text(text)
            if should_find:
                self.assertGreater(len(part_numbers), 0, f"Failed to extract from: {text}")


class TestPartStatusClassifierIntegration(unittest.TestCase):
    """Integration tests for classifier (requires transformers)."""

    def setUp(self):
        """Set up test fixtures."""
        try:
            import transformers
            self.has_transformers = True
            self.classifier = PartStatusClassifier()
        except ImportError:
            self.has_transformers = False
            self.skipTest("transformers library not installed")

    def test_classify_deprecation_status(self):
        """Test deprecation classification."""
        if not self.has_transformers:
            self.skipTest("transformers not available")

        text = "This part has been discontinued"
        result = self.classifier.classify_deprecation_status(text, threshold=0.3)

        self.assertIn("is_deprecated", result)
        self.assertIn("deprecation_indicators", result)
        self.assertIsInstance(result["is_deprecated"], bool)

    def test_classify_replacement_info(self):
        """Test replacement classification."""
        if not self.has_transformers:
            self.skipTest("transformers not available")

        text = "This part is replaced by part XYZ123"
        result = self.classifier.classify_replacement_info(text, threshold=0.3)

        self.assertIn("has_replacement_info", result)
        self.assertIn("replacement_indicators", result)
        self.assertIsInstance(result["has_replacement_info"], bool)

    def test_classify_compatibility(self):
        """Test compatibility classification."""
        if not self.has_transformers:
            self.skipTest("transformers not available")

        text = "This part is compatible with model ABC"
        result = self.classifier.classify_compatibility(text, threshold=0.3)

        self.assertIn("has_compatibility_info", result)
        self.assertIn("compatibility_indicators", result)
        self.assertIsInstance(result["has_compatibility_info"], bool)

    def test_classify_all(self):
        """Test classifying all categories at once."""
        if not self.has_transformers:
            self.skipTest("transformers not available")

        text = "Part ABC123 is obsolete. Use replacement XYZ456 instead."
        result = self.classifier.classify_all(text, threshold=0.3)

        self.assertIn("deprecation", result)
        self.assertIn("replacement", result)
        self.assertIn("compatibility", result)


if __name__ == '__main__':
    unittest.main()
