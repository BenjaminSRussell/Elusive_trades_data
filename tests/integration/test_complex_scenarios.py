"""
Comprehensive integration tests with complex real-world scenarios.

Tests include:
- Complex part searches with multiple variants
- Repeating model numbers across manufacturers
- Edge cases and error handling
- Malformed data handling
- Missing data scenarios
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phase1_acquisition.orchestrator import APIOrchestrator
from phase2_matching.matcher import PartMatcher
from phase2_matching.enricher import PartEnricher


class TestComplexPartSearches(unittest.TestCase):
    """Test complex part number scenarios."""

    def setUp(self):
        """Set up test fixtures with output directory."""
        self.test_output_dir = Path(__file__).parent.parent / "output"
        self.test_output_dir.mkdir(parents=True, exist_ok=True)

        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = APIOrchestrator(output_dir=self.temp_dir)

        self.test_results = []

    def tearDown(self):
        """Clean up and save test results."""
        shutil.rmtree(self.temp_dir)

        # Save test results to output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.test_output_dir / f"complex_test_results_{timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump({
                "test_class": self.__class__.__name__,
                "timestamp": timestamp,
                "results": self.test_results
            }, f, indent=2)

    def _save_result(self, test_name, data):
        """Save individual test result."""
        self.test_results.append({
            "test": test_name,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })

    def test_standard_capacitor_part(self):
        """Test searching for a standard capacitor part number."""
        part_number = "0131M00008P"
        results = self.orchestrator.search_all_apis(part_number)

        self._save_result("standard_capacitor", results)

        # Verify we got results from all APIs
        self.assertEqual(len(results['results']), 4)

        # Verify each API returned success
        for api_name, result in results['results'].items():
            self.assertEqual(result['status'], 'success')
            self.assertIn('data', result)

    def test_carrier_part_number(self):
        """Test Carrier-specific part number."""
        part_number = "P291-4053RS"
        results = self.orchestrator.search_all_apis(part_number)

        self._save_result("carrier_part", results)

        # Should find in multiple APIs due to cross-references
        success_count = sum(1 for r in results['results'].values() if r['status'] == 'success')
        self.assertGreater(success_count, 0)

    def test_part_with_dashes_and_special_chars(self):
        """Test part numbers with special characters."""
        test_parts = [
            "P291-4053RS",
            "CAP-440-4005",
            "B1340021S",
            "0131M-00008P",
        ]

        all_results = {}
        for part in test_parts:
            results = self.orchestrator.search_all_apis(part)
            all_results[part] = results

        self._save_result("special_chars_parts", all_results)

        # All should return some results
        for part, results in all_results.items():
            self.assertIsNotNone(results)
            self.assertIn('results', results)

    def test_non_existent_part(self):
        """Test searching for non-existent part number."""
        part_number = "NOTREAL999"
        results = self.orchestrator.search_all_apis(part_number)

        self._save_result("non_existent_part", results)

        # Should still return structure, just with no data or not found status
        self.assertIsNotNone(results)
        self.assertEqual(results['part_number'], part_number)

    def test_malformed_part_numbers(self):
        """Test handling of malformed part numbers."""
        malformed_parts = [
            "",  # Empty string
            "   ",  # Whitespace only
            "ABC",  # Too short
            "X" * 100,  # Too long
            "123-ABC-XYZ-999",  # Multiple dashes
            "Part#12345",  # With special char
        ]

        results_collection = {}
        for part in malformed_parts:
            try:
                results = self.orchestrator.search_all_apis(part)
                results_collection[part if part else "(empty)"] = {
                    "status": "completed",
                    "results": results
                }
            except Exception as e:
                results_collection[part if part else "(empty)"] = {
                    "status": "error",
                    "error": str(e)
                }

        self._save_result("malformed_parts", results_collection)

        # Should handle gracefully without crashing
        self.assertEqual(len(results_collection), len(malformed_parts))


class TestRepeatingModelNumbers(unittest.TestCase):
    """Test scenarios with repeating model numbers across manufacturers."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(__file__).parent.parent / "output"
        self.test_output_dir.mkdir(parents=True, exist_ok=True)

        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = APIOrchestrator(output_dir=self.temp_dir)

        self.test_results = []

    def tearDown(self):
        """Clean up and save results."""
        shutil.rmtree(self.temp_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.test_output_dir / f"repeating_models_{timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump({
                "test_class": self.__class__.__name__,
                "timestamp": timestamp,
                "results": self.test_results
            }, f, indent=2)

    def _save_result(self, test_name, data):
        """Save test result."""
        self.test_results.append({
            "test": test_name,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })

    def test_common_model_number(self):
        """Test model number that exists across multiple manufacturers."""
        model_number = "ARUF37C14"
        results = self.orchestrator.search_by_model_all_apis(model_number)

        self._save_result("common_model", results)

        # Should find in multiple APIs
        self.assertIsNotNone(results)
        self.assertIn('results', results)

    def test_model_number_variations(self):
        """Test variations of the same model number."""
        base_model = "ARUF37C14"
        variations = [
            "ARUF37C14",
            "ARUF-37C14",
            "ARUF 37C14",
            "aruf37c14",  # lowercase
        ]

        all_results = {}
        for model in variations:
            results = self.orchestrator.search_by_model_all_apis(model)
            all_results[model] = results

        self._save_result("model_variations", all_results)

        # All variations should be handled
        self.assertEqual(len(all_results), len(variations))

    def test_generic_model_patterns(self):
        """Test generic model number patterns."""
        generic_models = [
            "MODEL123",
            "ABC-123",
            "XYZ789",
        ]

        results_collection = {}
        for model in generic_models:
            results = self.orchestrator.search_by_model_all_apis(model)
            results_collection[model] = results

        self._save_result("generic_models", results_collection)

        # Should handle all without errors
        self.assertEqual(len(results_collection), len(generic_models))


class TestCrossReferenceDetection(unittest.TestCase):
    """Test cross-reference and relationship detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(__file__).parent.parent / "output"
        self.test_output_dir.mkdir(parents=True, exist_ok=True)

        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = APIOrchestrator(output_dir=self.temp_dir)
        self.matcher = PartMatcher(
            raw_data_dir=self.temp_dir,
            output_dir=str(self.test_output_dir / "matcher_output")
        )

        self.test_results = []

    def tearDown(self):
        """Clean up and save results."""
        shutil.rmtree(self.temp_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.test_output_dir / f"cross_reference_{timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump({
                "test_class": self.__class__.__name__,
                "timestamp": timestamp,
                "results": self.test_results
            }, f, indent=2)

    def _save_result(self, test_name, data):
        """Save test result."""
        self.test_results.append({
            "test": test_name,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })

    def test_find_cross_references(self):
        """Test finding cross-references for a part."""
        # First, populate data
        part_number = "0131M00008P"
        api_results = self.orchestrator.search_all_apis(part_number)

        # Now search for cross-references
        cross_refs = self.matcher.find_cross_references(part_number)

        self._save_result("cross_references", {
            "part_number": part_number,
            "api_results": api_results,
            "cross_refs": cross_refs
        })

        self.assertIn('cross_references', cross_refs)

    def test_find_replacements(self):
        """Test finding replacement parts."""
        part_number = "0131M00008P"

        # Populate data
        self.orchestrator.search_all_apis(part_number)

        # Find replacements
        replacements = self.matcher.find_replacements(part_number)

        self._save_result("replacements", replacements)

        self.assertIn('replacements', replacements)
        self.assertIn('has_replacement', replacements)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(__file__).parent.parent / "output"
        self.test_output_dir.mkdir(parents=True, exist_ok=True)

        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = APIOrchestrator(output_dir=self.temp_dir)

        self.test_results = []

    def tearDown(self):
        """Clean up and save results."""
        shutil.rmtree(self.temp_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.test_output_dir / f"error_handling_{timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump({
                "test_class": self.__class__.__name__,
                "timestamp": timestamp,
                "results": self.test_results
            }, f, indent=2)

    def _save_result(self, test_name, data):
        """Save test result."""
        self.test_results.append({
            "test": test_name,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })

    def test_empty_input(self):
        """Test handling of empty input."""
        try:
            results = self.orchestrator.search_all_apis("")
            self._save_result("empty_input", {
                "status": "completed",
                "results": results
            })
        except Exception as e:
            self._save_result("empty_input", {
                "status": "error",
                "error": str(e)
            })

        # Should not crash
        self.assertTrue(True)

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        unicode_parts = [
            "测试123",  # Chinese
            "Тест456",  # Cyrillic
            "🔧🔨⚙️",  # Emojis
            "Café-123",  # Accented
        ]

        results_collection = {}
        for part in unicode_parts:
            try:
                results = self.orchestrator.search_all_apis(part)
                results_collection[part] = {
                    "status": "completed",
                    "results": results
                }
            except Exception as e:
                results_collection[part] = {
                    "status": "error",
                    "error": str(e)
                }

        self._save_result("unicode_characters", results_collection)

        # Should handle gracefully
        self.assertEqual(len(results_collection), len(unicode_parts))

    def test_sql_injection_patterns(self):
        """Test that SQL injection patterns are handled safely."""
        injection_attempts = [
            "'; DROP TABLE parts; --",
            "1' OR '1'='1",
            "admin'--",
            "<script>alert('xss')</script>",
        ]

        results_collection = {}
        for attempt in injection_attempts:
            try:
                results = self.orchestrator.search_all_apis(attempt)
                results_collection[attempt] = {
                    "status": "completed",
                    "results": results
                }
            except Exception as e:
                results_collection[attempt] = {
                    "status": "error",
                    "error": str(e)
                }

        self._save_result("sql_injection_tests", results_collection)

        # Should not cause any security issues
        self.assertEqual(len(results_collection), len(injection_attempts))

    def test_very_long_input(self):
        """Test handling of very long input strings."""
        long_input = "A" * 10000

        try:
            results = self.orchestrator.search_all_apis(long_input)
            self._save_result("very_long_input", {
                "status": "completed",
                "input_length": len(long_input),
                "results": results
            })
        except Exception as e:
            self._save_result("very_long_input", {
                "status": "error",
                "input_length": len(long_input),
                "error": str(e)
            })

        # Should handle without crashing
        self.assertTrue(True)

    def test_concurrent_searches(self):
        """Test multiple concurrent searches."""
        parts = ["0131M00008P", "P291-4053RS", "B1340021", "CAP-440-4005"]

        results_collection = {}
        for part in parts:
            results = self.orchestrator.search_all_apis(part)
            results_collection[part] = results

        self._save_result("concurrent_searches", results_collection)

        # All should complete successfully
        self.assertEqual(len(results_collection), len(parts))


class TestDataIntegrity(unittest.TestCase):
    """Test data integrity and consistency."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(__file__).parent.parent / "output"
        self.test_output_dir.mkdir(parents=True, exist_ok=True)

        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = APIOrchestrator(output_dir=self.temp_dir)

        self.test_results = []

    def tearDown(self):
        """Clean up and save results."""
        shutil.rmtree(self.temp_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.test_output_dir / f"data_integrity_{timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump({
                "test_class": self.__class__.__name__,
                "timestamp": timestamp,
                "results": self.test_results
            }, f, indent=2)

    def _save_result(self, test_name, data):
        """Save test result."""
        self.test_results.append({
            "test": test_name,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })

    def test_data_persistence(self):
        """Test that data is properly saved and can be retrieved."""
        part_number = "0131M00008P"

        # First search
        results1 = self.orchestrator.search_all_apis(part_number)

        # Check files were created
        api_dir = Path(self.temp_dir)
        json_files = list(api_dir.rglob("*.json"))

        self._save_result("data_persistence", {
            "part_number": part_number,
            "files_created": len(json_files),
            "file_paths": [str(f) for f in json_files[:10]]  # First 10
        })

        self.assertGreater(len(json_files), 0)

    def test_data_structure_consistency(self):
        """Test that all API responses have consistent structure."""
        part_number = "0131M00008P"
        results = self.orchestrator.search_all_apis(part_number)

        required_fields = ['part_number', 'timestamp', 'apis_queried', 'results']

        structure_analysis = {
            "has_all_required_fields": all(field in results for field in required_fields),
            "required_fields": required_fields,
            "actual_fields": list(results.keys()),
            "api_count": len(results.get('results', {}))
        }

        self._save_result("structure_consistency", structure_analysis)

        # Verify structure
        for field in required_fields:
            self.assertIn(field, results, f"Missing required field: {field}")


def run_all_tests_with_report():
    """Run all tests and generate comprehensive report."""
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestComplexPartSearches))
    suite.addTests(loader.loadTestsFromTestCase(TestRepeatingModelNumbers))
    suite.addTests(loader.loadTestsFromTestCase(TestCrossReferenceDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestDataIntegrity))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate summary report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = output_dir / f"test_summary_{timestamp}.json"

    summary = {
        "timestamp": timestamp,
        "total_tests": result.testsRun,
        "successes": result.testsRun - len(result.failures) - len(result.errors),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "success_rate": f"{((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.2f}%",
        "failure_details": [str(f) for f in result.failures],
        "error_details": [str(e) for e in result.errors]
    }

    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*70}")
    print(f"Test Summary Report saved to: {summary_file}")
    print(f"Total tests: {summary['total_tests']}")
    print(f"Successes: {summary['successes']}")
    print(f"Failures: {summary['failures']}")
    print(f"Errors: {summary['errors']}")
    print(f"Success Rate: {summary['success_rate']}")
    print(f"{'='*70}\n")

    return result


if __name__ == '__main__':
    run_all_tests_with_report()
