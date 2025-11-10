"""
TDD Tests for Carrier API adapter.
"""

import unittest
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phase1_acquisition.apis.carrier_api import CarrierAPI


class TestCarrierAPI(unittest.TestCase):
    """Test cases for Carrier API adapter."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.api = CarrierAPI(output_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test Carrier API initialization."""
        self.assertIsNotNone(self.api)
        self.assertEqual(self.api.api_name, "carrier")

    def test_search_by_part_number(self):
        """Test searching by part number."""
        result = self.api.search_by_part_number("P291-4053RS")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["api"], "carrier")

    def test_search_by_model(self):
        """Test searching by model number."""
        result = self.api.search_by_model("MODEL123")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["api"], "carrier")

    def test_get_part_details(self):
        """Test getting part details."""
        result = self.api.get_part_details("P291-4053RS")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["api"], "carrier")

    def test_get_available_endpoints(self):
        """Test getting available endpoints."""
        endpoints = self.api.get_available_endpoints()
        self.assertIsInstance(endpoints, list)
        self.assertGreater(len(endpoints), 0)


if __name__ == '__main__':
    unittest.main()
