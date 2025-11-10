"""
TDD Tests for Goodman API adapter.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phase1_acquisition.apis.goodman_api import GoodmanAPI


class TestGoodmanAPI(unittest.TestCase):
    """Test cases for Goodman API adapter."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.api = GoodmanAPI(output_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test Goodman API initialization."""
        self.assertIsNotNone(self.api)
        self.assertEqual(self.api.api_name, "goodman")
        self.assertTrue(hasattr(self.api, 'session'))
        self.assertTrue(hasattr(self.api, 'timeout'))

    def test_search_by_part_number(self):
        """Test searching by part number."""
        part_number = "0131M00008P"
        result = self.api.search_by_part_number(part_number)

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("api", result)
        self.assertIn("part_number", result)
        self.assertIn("status", result)

        self.assertEqual(result["api"], "goodman")
        self.assertEqual(result["part_number"], part_number)

    def test_search_by_part_number_saves_file(self):
        """Test that search results are saved to file."""
        part_number = "0131M00008P"
        self.api.search_by_part_number(part_number)

        # Check that file was saved
        expected_file = self.api.api_output_dir / f"part_{part_number}.json"
        self.assertTrue(expected_file.exists())

        # Verify content
        with open(expected_file, 'r') as f:
            data = json.load(f)

        self.assertEqual(data["part_number"], part_number)

    def test_search_by_model(self):
        """Test searching by model number."""
        model_number = "ARUF37C14"
        result = self.api.search_by_model(model_number)

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("api", result)
        self.assertIn("model_number", result)
        self.assertIn("status", result)

        self.assertEqual(result["api"], "goodman")
        self.assertEqual(result["model_number"], model_number)

    def test_get_part_details(self):
        """Test getting part details."""
        part_id = "0131M00008P"
        result = self.api.get_part_details(part_id)

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("api", result)
        self.assertIn("part_id", result)
        self.assertIn("status", result)

        self.assertEqual(result["api"], "goodman")
        self.assertEqual(result["part_id"], part_id)

    def test_search_cross_references(self):
        """Test searching for cross-references."""
        part_number = "0131M00008P"
        result = self.api.search_cross_references(part_number)

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("api", result)
        self.assertIn("source_part", result)
        self.assertIn("cross_references", result)

        self.assertEqual(result["api"], "goodman")
        self.assertEqual(result["source_part"], part_number)
        self.assertIsInstance(result["cross_references"], list)

    def test_get_available_endpoints(self):
        """Test getting available endpoints."""
        endpoints = self.api.get_available_endpoints()

        self.assertIsInstance(endpoints, list)
        self.assertGreater(len(endpoints), 0)

        # Verify endpoint descriptions contain method names
        endpoint_str = " ".join(endpoints)
        self.assertIn("search_by_part_number", endpoint_str)
        self.assertIn("search_by_model", endpoint_str)
        self.assertIn("get_part_details", endpoint_str)

    def test_session_headers(self):
        """Test that session has proper headers."""
        self.assertIn('User-Agent', self.api.session.headers)
        self.assertIn('Accept', self.api.session.headers)
        self.assertEqual(self.api.session.headers['Accept'], 'application/json')

    def test_base_url_configured(self):
        """Test that BASE_URL is configured."""
        self.assertTrue(hasattr(GoodmanAPI, 'BASE_URL'))
        self.assertIsInstance(GoodmanAPI.BASE_URL, str)
        self.assertGreater(len(GoodmanAPI.BASE_URL), 0)

    def test_timeout_configuration(self):
        """Test timeout configuration."""
        custom_timeout = 60
        api = GoodmanAPI(output_dir=self.temp_dir, timeout=custom_timeout)
        self.assertEqual(api.timeout, custom_timeout)

    def test_multiple_searches_different_files(self):
        """Test that multiple searches create separate files."""
        part1 = "0131M00008P"
        part2 = "B1340021"

        self.api.search_by_part_number(part1)
        self.api.search_by_part_number(part2)

        # Verify both files exist
        file1 = self.api.api_output_dir / f"part_{part1}.json"
        file2 = self.api.api_output_dir / f"part_{part2}.json"

        self.assertTrue(file1.exists())
        self.assertTrue(file2.exists())


class TestGoodmanAPIDataStructure(unittest.TestCase):
    """Test the structure of data returned by Goodman API."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.api = GoodmanAPI(output_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_part_search_data_structure(self):
        """Test that part search returns expected data structure."""
        result = self.api.search_by_part_number("0131M00008P")

        # Top level fields
        self.assertIn("data", result)

        # Data fields (when status is "found")
        if result["status"] == "found":
            data = result["data"]
            self.assertIn("part_number", data)
            self.assertIn("description", data)
            self.assertIn("manufacturer", data)

    def test_model_search_data_structure(self):
        """Test that model search returns expected data structure."""
        result = self.api.search_by_model("ARUF37C14")

        if result["status"] == "found":
            self.assertIn("data", result)
            data = result["data"]
            self.assertIn("model", data)
            self.assertIn("parts", data)
            self.assertIsInstance(data["parts"], list)

    def test_part_details_data_structure(self):
        """Test that part details returns expected data structure."""
        result = self.api.get_part_details("0131M00008P")

        if result["status"] == "found":
            self.assertIn("data", result)
            data = result["data"]
            self.assertIn("part_number", data)
            self.assertIn("manufacturer", data)


if __name__ == '__main__':
    unittest.main()
