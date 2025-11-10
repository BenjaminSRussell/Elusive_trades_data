"""
TDD Tests for PartMatcher.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phase2_matching.matcher import PartMatcher


class TestPartMatcher(unittest.TestCase):
    """Test cases for PartMatcher."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.raw_data_dir = Path(self.temp_dir) / "raw"
        self.processed_dir = Path(self.temp_dir) / "processed"

        self.matcher = PartMatcher(
            raw_data_dir=str(self.raw_data_dir),
            output_dir=str(self.processed_dir)
        )

        # Create test data structure
        self._create_test_data()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def _create_test_data(self):
        """Create test API data."""
        # Create Goodman API test data
        goodman_dir = self.raw_data_dir / "goodman" / "20240101_120000"
        goodman_dir.mkdir(parents=True)

        test_part_data = {
            "api": "goodman",
            "part_number": "0131M00008P",
            "status": "found",
            "data": {
                "part_number": "0131M00008P",
                "description": "Capacitor 40+5 MFD",
                "manufacturer": "Goodman",
                "cross_references": [
                    {
                        "manufacturer": "Carrier",
                        "part_number": "P291-4053RS"
                    }
                ],
                "replacements": []
            }
        }

        with open(goodman_dir / "part_0131M00008P.json", 'w') as f:
            json.dump(test_part_data, f)

    def test_initialization(self):
        """Test matcher initialization."""
        self.assertIsNotNone(self.matcher)
        self.assertTrue(self.matcher.output_dir.exists())

    def test_search_part_with_data(self):
        """Test searching for a part that exists in the data."""
        result = self.matcher.search_part("0131M00008P")

        self.assertIn("part_number", result)
        self.assertIn("matches", result)
        self.assertIn("summary", result)

        self.assertEqual(result["part_number"], "0131M00008P")
        self.assertGreater(result["summary"]["total_matches"], 0)

    def test_search_part_no_data(self):
        """Test searching for a part with no data."""
        result = self.matcher.search_part("NONEXISTENT")

        self.assertEqual(result["summary"]["total_matches"], 0)
        self.assertEqual(len(result["matches"]), 0)

    def test_normalize_part_number(self):
        """Test part number normalization."""
        tests = [
            ("0131M00008P", "0131M00008P"),
            ("0131M-00008P", "0131M00008P"),
            ("0131m 00008p", "0131M00008P"),
            ("P291-4053RS", "P2914053RS")
        ]

        for input_pn, expected in tests:
            result = self.matcher._normalize_part_number(input_pn)
            self.assertEqual(result, expected)

    def test_find_cross_references(self):
        """Test finding cross-references."""
        result = self.matcher.find_cross_references("0131M00008P")

        self.assertIn("source_part", result)
        self.assertIn("cross_references", result)
        self.assertIn("total_found", result)

    def test_find_replacements(self):
        """Test finding replacements."""
        result = self.matcher.find_replacements("0131M00008P")

        self.assertIn("original_part", result)
        self.assertIn("replacements", result)
        self.assertIn("has_replacement", result)

    def test_save_match_results(self):
        """Test that match results are saved."""
        result = self.matcher.search_part("0131M00008P")

        # Check that file was created
        normalized = self.matcher._normalize_part_number("0131M00008P")
        part_dir = self.matcher.output_dir / normalized

        self.assertTrue(part_dir.exists())

        # Find the saved file
        saved_files = list(part_dir.glob("match_results_*.json"))
        self.assertGreater(len(saved_files), 0)

    def test_get_part_history_empty(self):
        """Test getting history for part with no history."""
        history = self.matcher.get_part_history("NEWPART")
        self.assertEqual(len(history), 0)

    def test_get_part_history_with_data(self):
        """Test getting history for part with previous searches."""
        # Perform a search to create history
        self.matcher.search_part("0131M00008P")

        # Get history
        history = self.matcher.get_part_history("0131M00008P")

        self.assertGreater(len(history), 0)
        self.assertIsInstance(history[0], dict)

    def test_contains_part_number_dict(self):
        """Test _contains_part_number with dictionary."""
        data = {
            "part_number": "0131M00008P",
            "description": "Test"
        }

        self.assertTrue(self.matcher._contains_part_number(data, "0131M00008P"))
        self.assertFalse(self.matcher._contains_part_number(data, "NOTFOUND"))

    def test_contains_part_number_nested(self):
        """Test _contains_part_number with nested data."""
        data = {
            "data": {
                "parts": [
                    {"part_number": "0131M00008P"}
                ]
            }
        }

        self.assertTrue(self.matcher._contains_part_number(data, "0131M00008P"))

    def test_contains_part_number_case_insensitive(self):
        """Test that part number search is case insensitive."""
        data = {"part_number": "0131m00008p"}

        self.assertTrue(self.matcher._contains_part_number(data, "0131M00008P"))

    def test_extract_relationships(self):
        """Test extracting relationships from matches."""
        results = {
            "matches": [
                {
                    "data": {
                        "cross_references": [
                            {"part_number": "TEST123"}
                        ],
                        "replacements": [
                            {"part_number": "TEST456"}
                        ]
                    }
                }
            ],
            "cross_references": [],
            "replacements": [],
            "summary": {
                "has_replacement": False
            }
        }

        self.matcher._extract_relationships(results)

        self.assertGreater(len(results["cross_references"]), 0)
        self.assertGreater(len(results["replacements"]), 0)


if __name__ == '__main__':
    unittest.main()
