"""Offline tests for Johnstone API adapter (mock mode, no live hosts)."""

import os
import json
import unittest
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

os.environ.setdefault("ACQUISITION_MODE", "mock")

from phase1_acquisition.apis.johnstone_api import JohnstoneAPI


class TestJohnstoneAPI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.api = JohnstoneAPI(output_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        self.assertEqual(self.api.api_name, "johnstone")
        self.assertTrue(hasattr(self.api, "session"))
        self.assertTrue(hasattr(JohnstoneAPI, "BASE_URL"))

    def test_fixture_part_hit(self):
        result = self.api.search_by_part_number("C4405R")
        self.assertEqual(result["api"], "johnstone")
        self.assertEqual(result["part_number"], "C4405R")
        self.assertEqual(result["status"], "found")
        self.assertIn("data", result)
        self.assertEqual(result["data"]["description"], "Dual Run Capacitor 40+5 MFD")

    def test_unknown_part_not_found(self):
        result = self.api.search_by_part_number("NONEXISTENT")
        self.assertEqual(result["status"], "not_found")
        self.assertEqual(result["api"], "johnstone")

    def test_search_saves_file(self):
        self.api.search_by_part_number("C4405R")
        expected = self.api.api_output_dir / "part_C4405R.json"
        self.assertTrue(expected.exists())
        with open(expected) as f:
            data = json.load(f)
        self.assertEqual(data["part_number"], "C4405R")

    def test_search_by_model_shape(self):
        result = self.api.search_by_model("MODEL123")
        self.assertEqual(result["api"], "johnstone")
        self.assertEqual(result["model_number"], "MODEL123")
        self.assertIn("status", result)

    def test_get_part_details_shape(self):
        result = self.api.get_part_details("C4405R")
        self.assertEqual(result["api"], "johnstone")
        self.assertIn("status", result)

    def test_get_available_endpoints(self):
        endpoints = self.api.get_available_endpoints()
        self.assertIsInstance(endpoints, list)
        joined = " ".join(endpoints)
        self.assertIn("search_by_part_number", joined)


if __name__ == "__main__":
    unittest.main()
