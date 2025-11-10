"""
TDD Tests for BaseAPI abstract class.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phase1_acquisition.apis.base_api import BaseAPI


class ConcreteAPI(BaseAPI):
    """Concrete implementation for testing."""

    def search_by_part_number(self, part_number: str):
        return {"part_number": part_number, "status": "found"}

    def search_by_model(self, model_number: str):
        return {"model_number": model_number, "status": "found"}

    def get_part_details(self, part_id: str):
        return {"part_id": part_id, "details": "test"}

    def get_available_endpoints(self):
        return ["test_endpoint"]


class TestBaseAPI(unittest.TestCase):
    """Test cases for BaseAPI."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.api = ConcreteAPI(output_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test API initialization."""
        self.assertIsNotNone(self.api)
        self.assertEqual(self.api.api_name, "concrete")
        self.assertTrue(self.api.api_output_dir.exists())

    def test_output_directory_creation(self):
        """Test that output directory is created."""
        expected_path = Path(self.temp_dir) / "concrete"
        self.assertTrue(expected_path.exists())
        self.assertTrue(expected_path.is_dir())

    def test_save_response(self):
        """Test saving API response to file."""
        test_data = {
            "part_number": "TEST123",
            "description": "Test Part"
        }

        filepath = self.api.save_response(test_data, "test_part")

        # Verify file was created
        self.assertTrue(filepath.exists())
        self.assertEqual(filepath.suffix, ".json")

        # Verify content
        with open(filepath, 'r') as f:
            loaded_data = json.load(f)

        self.assertEqual(loaded_data, test_data)

    def test_load_response(self):
        """Test loading previously saved response."""
        test_data = {
            "part_number": "TEST456",
            "description": "Another Test Part"
        }

        # Save first
        self.api.save_response(test_data, "test_load")

        # Load
        loaded_data = self.api.load_response("test_load")

        self.assertIsNotNone(loaded_data)
        self.assertEqual(loaded_data, test_data)

    def test_load_nonexistent_response(self):
        """Test loading a response that doesn't exist."""
        result = self.api.load_response("nonexistent")
        self.assertIsNone(result)

    def test_get_api_info(self):
        """Test getting API metadata."""
        info = self.api.get_api_info()

        self.assertIn("name", info)
        self.assertIn("output_dir", info)
        self.assertIn("session_timestamp", info)
        self.assertIn("endpoints", info)

        self.assertEqual(info["name"], "concrete")
        self.assertEqual(info["endpoints"], ["test_endpoint"])

    def test_abstract_methods_must_be_implemented(self):
        """Test that abstract methods must be implemented."""
        with self.assertRaises(TypeError):
            # This should fail because BaseAPI can't be instantiated
            BaseAPI(output_dir=self.temp_dir)

    def test_repr(self):
        """Test string representation."""
        repr_str = repr(self.api)
        self.assertIn("ConcreteAPI", repr_str)
        self.assertIn("output_dir", repr_str)


class TestAPIMethodSignatures(unittest.TestCase):
    """Test that concrete implementations have correct method signatures."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.api = ConcreteAPI(output_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_search_by_part_number_signature(self):
        """Test search_by_part_number method signature."""
        result = self.api.search_by_part_number("TEST123")
        self.assertIsInstance(result, dict)
        self.assertIn("part_number", result)

    def test_search_by_model_signature(self):
        """Test search_by_model method signature."""
        result = self.api.search_by_model("MODEL123")
        self.assertIsInstance(result, dict)
        self.assertIn("model_number", result)

    def test_get_part_details_signature(self):
        """Test get_part_details method signature."""
        result = self.api.get_part_details("PART123")
        self.assertIsInstance(result, dict)
        self.assertIn("part_id", result)

    def test_get_available_endpoints_signature(self):
        """Test get_available_endpoints method signature."""
        result = self.api.get_available_endpoints()
        self.assertIsInstance(result, list)


if __name__ == '__main__':
    unittest.main()
