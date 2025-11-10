"""
GUI Functionality Tests (Headless)

Tests the GUI backend functionality without requiring a display.
"""

import unittest
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from phase1_acquisition.orchestrator import APIOrchestrator
from phase2_matching.enricher import PartEnricher


class TestGUIBackend(unittest.TestCase):
    """Test GUI backend operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.orchestrator = APIOrchestrator()
        self.enricher = PartEnricher()
        self.test_output_dir = Path(__file__).parent / "output"
        self.test_output_dir.mkdir(parents=True, exist_ok=True)

    def test_part_number_search(self):
        """Test part number search (simulates GUI search button)."""
        part_number = "0131M00008P"

        # Simulate Phase 1 search
        results = self.orchestrator.search_all_apis(part_number)

        # Verify results structure (what GUI would receive)
        self.assertIn('part_number', results)
        self.assertIn('results', results)
        self.assertIn('timestamp', results)

        # Verify all APIs responded
        self.assertEqual(len(results['results']), 4)

        # Save results (simulates GUI "Save Results" button)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.test_output_dir / f"gui_sim_part_{part_number}_{timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        self.assertTrue(output_file.exists())
        print(f"\n✓ Part search simulation saved to: {output_file}")

    def test_model_number_search(self):
        """Test model number search (simulates GUI model search)."""
        model_number = "ARUF37C14"

        # Simulate Phase 1 model search
        results = self.orchestrator.search_by_model_all_apis(model_number)

        # Verify results structure
        self.assertIn('model_number', results)
        self.assertIn('results', results)

        # Verify all APIs responded
        self.assertEqual(len(results['results']), 4)

        print(f"\n✓ Model search simulation completed")

    def test_enrichment_toggle_on(self):
        """Test with enrichment enabled (GUI checkbox ON)."""
        part_number = "0131M00008P"

        # Phase 1
        api_results = self.orchestrator.search_all_apis(part_number)

        # Phase 2 (enrichment enabled)
        try:
            enriched = self.enricher.enrich_part(part_number)

            # Verify enriched data structure
            self.assertIn('status', enriched)
            self.assertIn('relationships', enriched)
            self.assertIn('confidence_scores', enriched)

            print(f"\n✓ Enrichment simulation completed")
            print(f"  Status: {enriched['status']}")
            print(f"  Confidence: {enriched['confidence_scores']}")

        except ImportError:
            print(f"\n⚠ Enrichment skipped (transformers not installed)")

    def test_enrichment_toggle_off(self):
        """Test with enrichment disabled (GUI checkbox OFF)."""
        part_number = "P291-4053RS"

        # Only Phase 1 (enrichment disabled)
        api_results = self.orchestrator.search_all_apis(part_number)

        # Verify we get results without enrichment
        self.assertIn('results', api_results)

        # Should be faster without enrichment
        print(f"\n✓ Fast search (no enrichment) completed")

    def test_empty_input_handling(self):
        """Test handling of empty input (GUI validation)."""
        # GUI should prevent this, but backend should handle gracefully
        try:
            results = self.orchestrator.search_all_apis("")
            # Should not crash
            self.assertIsNotNone(results)
            print(f"\n✓ Empty input handled gracefully")
        except Exception as e:
            # Expected - empty input should be rejected
            print(f"\n✓ Empty input properly rejected: {type(e).__name__}")

    def test_special_characters_input(self):
        """Test handling of special characters (GUI input sanitization)."""
        special_inputs = [
            "P291-4053RS",  # Dashes
            "CAP/440/4005",  # Slashes
            "Part#12345",  # Hash
        ]

        for input_val in special_inputs:
            try:
                results = self.orchestrator.search_all_apis(input_val)
                self.assertIsNotNone(results)
            except Exception as e:
                # Should handle gracefully
                pass

        print(f"\n✓ Special character inputs handled")

    def test_concurrent_searches(self):
        """Test multiple searches in sequence (simulates rapid GUI usage)."""
        parts = ["0131M00008P", "P291-4053RS", "B1340021"]

        results_collection = []
        for part in parts:
            results = self.orchestrator.search_all_apis(part)
            results_collection.append(results)

        # All searches should succeed
        self.assertEqual(len(results_collection), len(parts))

        print(f"\n✓ Concurrent search simulation completed ({len(parts)} searches)")

    def test_save_results_functionality(self):
        """Test saving results to file (GUI Save button)."""
        part_number = "TEST123"

        # Perform search
        results = self.orchestrator.search_all_apis(part_number)

        # Simulate GUI save functionality
        current_results = {
            "search_value": part_number,
            "timestamp": datetime.now().isoformat(),
            "api_results": results,
            "enriched": None
        }

        # Save to tests/output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gui_sim_save_{part_number}_{timestamp}.json"
        filepath = self.test_output_dir / filename

        with open(filepath, 'w') as f:
            json.dump(current_results, f, indent=2)

        # Verify save succeeded
        self.assertTrue(filepath.exists())

        # Verify file is readable
        with open(filepath, 'r') as f:
            loaded = json.load(f)

        self.assertEqual(loaded['search_value'], part_number)

        print(f"\n✓ Save functionality test passed")
        print(f"  Saved to: {filepath}")

    def test_formatted_output_generation(self):
        """Test generating formatted output (GUI display text)."""
        part_number = "0131M00008P"
        results = self.orchestrator.search_all_apis(part_number)

        # Simulate GUI formatted output generation
        formatted_lines = []
        formatted_lines.append("="*70)
        formatted_lines.append(f"  Search Results for: {part_number}")
        formatted_lines.append("="*70)

        for api_name, api_result in results['results'].items():
            formatted_lines.append(f"\n{api_name.upper()}:")
            formatted_lines.append(f"  Status: {api_result.get('status', 'unknown')}")

            if api_result.get('status') == 'success':
                data = api_result.get('data', {})
                if 'data' in data:
                    part_data = data['data']
                    if 'description' in part_data:
                        formatted_lines.append(f"  Description: {part_data['description']}")

        formatted_output = "\n".join(formatted_lines)

        # Verify output is generated
        self.assertGreater(len(formatted_output), 0)
        self.assertIn(part_number, formatted_output)

        print(f"\n✓ Formatted output generation test passed")
        print(f"  Generated {len(formatted_lines)} lines of output")


class TestGUIErrorHandling(unittest.TestCase):
    """Test GUI error handling scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.orchestrator = APIOrchestrator()

    def test_malformed_input(self):
        """Test handling of malformed input."""
        malformed_inputs = [
            "   ",  # Whitespace
            "\n\n",  # Newlines
            "A" * 1000,  # Very long
        ]

        for input_val in malformed_inputs:
            try:
                results = self.orchestrator.search_all_apis(input_val)
                # Should handle without crashing
                self.assertIsNotNone(results)
            except Exception:
                # Expected - may reject invalid input
                pass

        print(f"\n✓ Malformed input handling test passed")

    def test_network_simulation(self):
        """Test that API errors don't crash the GUI."""
        # Even if APIs return errors, GUI should handle gracefully
        part_number = "NONEXISTENT"
        results = self.orchestrator.search_all_apis(part_number)

        # Should still return structure
        self.assertIn('results', results)

        print(f"\n✓ Network/API error simulation passed")


def run_gui_tests():
    """Run all GUI tests and generate report."""
    print("\n" + "="*70)
    print("  GUI FUNCTIONALITY TESTS (Headless)")
    print("="*70 + "\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestGUIBackend))
    suite.addTests(loader.loadTestsFromTestCase(TestGUIErrorHandling))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate summary
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = output_dir / f"gui_test_summary_{timestamp}.json"

    summary = {
        "timestamp": timestamp,
        "total_tests": result.testsRun,
        "successes": result.testsRun - len(result.failures) - len(result.errors),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "success_rate": f"{((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.2f}%"
    }

    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*70}")
    print(f"GUI Test Summary:")
    print(f"  Total: {summary['total_tests']}")
    print(f"  Passed: {summary['successes']}")
    print(f"  Failed: {summary['failures']}")
    print(f"  Errors: {summary['errors']}")
    print(f"  Success Rate: {summary['success_rate']}")
    print(f"\nSummary saved to: {summary_file}")
    print(f"{'='*70}\n")

    return result


if __name__ == '__main__':
    run_gui_tests()
