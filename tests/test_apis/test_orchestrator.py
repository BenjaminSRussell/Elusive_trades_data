"""
TDD Tests for API Orchestrator.
"""

import unittest
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phase1_acquisition.orchestrator import APIOrchestrator


class TestAPIOrchestrator(unittest.TestCase):
    """Test cases for API Orchestrator."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = APIOrchestrator(output_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test orchestrator initialization."""
        self.assertIsNotNone(self.orchestrator)
        self.assertGreater(len(self.orchestrator.apis), 0)

    def test_all_apis_loaded(self):
        """Test that all API adapters are loaded."""
        expected_apis = ['goodman', 'carrier', 'johnstone', 'ferguson']

        for api_name in expected_apis:
            self.assertIn(api_name, self.orchestrator.apis)

    def test_search_all_apis(self):
        """Test searching across all APIs."""
        part_number = "0131M00008P"
        results = self.orchestrator.search_all_apis(part_number)

        # Verify result structure
        self.assertIn("part_number", results)
        self.assertIn("results", results)
        self.assertIn("apis_queried", results)

        # Verify all APIs were queried
        self.assertEqual(len(results["results"]), len(self.orchestrator.apis))

    def test_search_specific_apis(self):
        """Test searching specific APIs only."""
        part_number = "0131M00008P"
        api_names = ['goodman', 'carrier']

        results = self.orchestrator.search_specific_apis(part_number, api_names)

        # Verify only specified APIs were queried
        self.assertEqual(len(results["results"]), len(api_names))
        for api_name in api_names:
            self.assertIn(api_name, results["results"])

    def test_get_part_details_from_all(self):
        """Test getting part details from all APIs."""
        part_number = "0131M00008P"
        results = self.orchestrator.get_part_details_from_all(part_number)

        self.assertIn("part_number", results)
        self.assertIn("details", results)
        self.assertEqual(len(results["details"]), len(self.orchestrator.apis))

    def test_search_by_model_all_apis(self):
        """Test searching by model across all APIs."""
        model_number = "ARUF37C14"
        results = self.orchestrator.search_by_model_all_apis(model_number)

        self.assertIn("model_number", results)
        self.assertIn("results", results)
        self.assertEqual(len(results["results"]), len(self.orchestrator.apis))

    def test_get_api_info(self):
        """Test getting API information."""
        info = self.orchestrator.get_api_info()

        self.assertIn("total_apis", info)
        self.assertIn("apis", info)
        self.assertEqual(info["total_apis"], len(self.orchestrator.apis))

    def test_add_api(self):
        """Test adding a new API adapter."""
        from phase1_acquisition.apis.base_api import BaseAPI

        class TestAPI(BaseAPI):
            def search_by_part_number(self, part_number: str):
                return {"test": "data"}

            def search_by_model(self, model_number: str):
                return {"test": "data"}

            def get_part_details(self, part_id: str):
                return {"test": "data"}

            def get_available_endpoints(self):
                return ["test"]

        initial_count = len(self.orchestrator.apis)
        test_api = TestAPI(output_dir=self.temp_dir)
        self.orchestrator.add_api("test_api", test_api)

        self.assertEqual(len(self.orchestrator.apis), initial_count + 1)
        self.assertIn("test_api", self.orchestrator.apis)

    def test_search_nonexistent_api(self):
        """Test searching with a nonexistent API name."""
        part_number = "0131M00008P"
        api_names = ['nonexistent_api']

        results = self.orchestrator.search_specific_apis(part_number, api_names)

        self.assertIn("nonexistent_api", results["results"])
        self.assertEqual(results["results"]["nonexistent_api"]["status"], "error")


if __name__ == '__main__':
    unittest.main()
