#!/usr/bin/env python3
"""
Demonstration script for HVAC Parts Search System

This script demonstrates the complete workflow:
1. Phase 1: Acquire data from all APIs
2. Phase 2: Enrich the data with matching and classification
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from phase1_acquisition.orchestrator import APIOrchestrator
from phase2_matching.enricher import PartEnricher


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def demo_phase1():
    """Demonstrate Phase 1: API data acquisition."""
    print_header("PHASE 1: API DATA ACQUISITION")

    # Initialize orchestrator
    print("Initializing API orchestrator...")
    orchestrator = APIOrchestrator()

    # Show available APIs
    api_info = orchestrator.get_api_info()
    print(f"✓ Loaded {api_info['total_apis']} API adapters:")
    for api_name in api_info['apis'].keys():
        print(f"  - {api_name}")

    # Test part number
    part_number = "0131M00008P"
    print(f"\n--- Searching all APIs for part: {part_number} ---")

    # Search across all APIs
    results = orchestrator.search_all_apis(part_number)

    print(f"\nSearch Results:")
    print(f"  Part number: {results['part_number']}")
    print(f"  APIs queried: {len(results['apis_queried'])}")
    print(f"  Timestamp: {results['timestamp']}")

    # Show results from each API
    print(f"\n  Results by API:")
    for api_name, result in results['results'].items():
        status = result['status']
        if status == 'success':
            data = result['data']
            api_status = data.get('status', 'unknown')
            print(f"    {api_name:12} - {status:8} (status: {api_status})")

            # Show part details if available
            if 'data' in data and isinstance(data['data'], dict):
                part_data = data['data']
                if 'description' in part_data:
                    print(f"      └─ {part_data['description']}")
        else:
            print(f"    {api_name:12} - {status}")

    # Test model search
    model_number = "ARUF37C14"
    print(f"\n--- Searching all APIs for model: {model_number} ---")

    model_results = orchestrator.search_by_model_all_apis(model_number)
    print(f"\nModel Search Results:")
    print(f"  Model number: {model_results['model_number']}")
    print(f"  APIs queried: {len(model_results['apis_queried'])}")

    for api_name, result in model_results['results'].items():
        status = result['status']
        print(f"    {api_name:12} - {status}")

    # Test specific API search
    print(f"\n--- Searching specific APIs (Goodman, Carrier) ---")

    specific_results = orchestrator.search_specific_apis(
        part_number,
        ['goodman', 'carrier']
    )

    print(f"\nSpecific API Search Results:")
    for api_name, result in specific_results['results'].items():
        print(f"    {api_name:12} - {result['status']}")

    return results


def demo_phase2(phase1_results):
    """Demonstrate Phase 2: Part matching and enrichment."""
    print_header("PHASE 2: PART MATCHING & ENRICHMENT")

    part_number = phase1_results['part_number']
    print(f"Enriching data for part: {part_number}")

    # Initialize enricher
    print("\nInitializing enricher (Matcher + Classifier)...")
    enricher = PartEnricher()

    # Note: Classifier requires transformers library
    # If not installed, matching will still work but classification will be skipped
    print("Note: Zero-shot classification requires 'transformers' library")
    print("      Install with: pip install transformers torch")

    # Perform enrichment (this will work even without transformers)
    print(f"\n--- Running enrichment pipeline ---")
    print("Steps:")
    print("  1. Searching Phase 1 data for part matches")
    print("  2. Extracting text from all sources")
    print("  3. Running zero-shot classification (if available)")
    print("  4. Extracting relationships and cross-references")
    print("  5. Calculating confidence scores")
    print("  6. Saving enriched data")

    try:
        enriched = enricher.enrich_part(part_number)

        print_header("ENRICHMENT RESULTS")

        # Summary
        print(f"Part Number: {enriched['part_number']}")
        print(f"Data Sources: {', '.join(enriched['data_sources'])}")
        print(f"Timestamp: {enriched['timestamp']}")

        # Status
        print(f"\n--- Part Status ---")
        status = enriched['status']
        print(f"  Is Deprecated: {status.get('is_deprecated', 'unknown')}")
        print(f"  Has Replacement: {status.get('has_replacement', 'unknown')}")
        print(f"  Has Compatibility Info: {status.get('has_compatibility_info', 'unknown')}")

        if status.get('is_deprecated'):
            confidence = status.get('deprecation_confidence', 0)
            print(f"  Deprecation Confidence: {confidence:.2%}")

        if status.get('has_replacement'):
            confidence = status.get('replacement_confidence', 0)
            print(f"  Replacement Confidence: {confidence:.2%}")

        # Relationships
        print(f"\n--- Relationships ---")
        relationships = enriched['relationships']
        print(f"  Cross References: {len(relationships.get('cross_references', []))}")
        print(f"  Replacements: {len(relationships.get('replacements', []))}")
        print(f"  Compatible Parts: {len(relationships.get('compatible_parts', []))}")

        # Show cross-references
        if relationships.get('cross_references'):
            print(f"\n  Cross-Reference Details:")
            for ref in relationships['cross_references'][:3]:  # Show first 3
                if isinstance(ref, dict):
                    mfr = ref.get('manufacturer', 'Unknown')
                    pn = ref.get('part_number', 'Unknown')
                    print(f"    - {mfr}: {pn}")

        # Confidence scores
        print(f"\n--- Confidence Scores ---")
        scores = enriched['confidence_scores']
        for key, value in scores.items():
            print(f"  {key:30} {value:.2%}")

        # Data locations
        print(f"\n--- Data Locations ---")
        print(f"  Raw API data: data/raw/")
        print(f"  Processed data: data/processed/{part_number}/")

        return enriched

    except ImportError as e:
        print(f"\n⚠ Warning: Some features not available")
        print(f"  {e}")
        print(f"\n  The matcher still works for basic functionality.")
        print(f"  To enable full classification, install: pip install transformers torch")
        return None
    except Exception as e:
        print(f"\n❌ Error during enrichment: {e}")
        import traceback
        traceback.print_exc()
        return None


def demo_individual_components():
    """Demonstrate using individual components."""
    print_header("INDIVIDUAL COMPONENT EXAMPLES")

    from phase1_acquisition.apis.goodman_api import GoodmanAPI
    from phase2_matching.matcher import PartMatcher
    from phase2_matching.classifier import PartStatusClassifier

    # Example 1: Single API
    print("--- Example 1: Using a single API ---")
    goodman = GoodmanAPI()
    result = goodman.search_by_part_number("0131M00008P")
    print(f"Goodman API result: {result['status']}")

    # Example 2: Matcher only
    print("\n--- Example 2: Using Matcher only ---")
    matcher = PartMatcher()
    match_results = matcher.search_part("0131M00008P")
    print(f"Total matches: {match_results['summary']['total_matches']}")
    print(f"APIs with data: {match_results['summary']['apis_with_data']}")

    # Example 3: Classifier only
    print("\n--- Example 3: Using Classifier only ---")
    classifier = PartStatusClassifier()

    # Extract part numbers
    text = "Part 0131M00008P is compatible with P291-4053RS and CAP050450440RU"
    part_numbers = classifier.extract_part_numbers_from_text(text)
    print(f"Text: {text}")
    print(f"Extracted part numbers: {part_numbers}")

    # Classification (if transformers available)
    try:
        text2 = "This capacitor has been discontinued and is no longer available"
        result = classifier.classify_deprecation_status(text2, threshold=0.3)
        print(f"\nText: {text2}")
        print(f"Is deprecated: {result['is_deprecated']}")
    except ImportError:
        print("\n(Classification skipped - transformers not installed)")


def main():
    """Main demonstration function."""
    print_header("HVAC PARTS SEARCH SYSTEM - DEMONSTRATION")

    print("This demo shows the complete workflow:")
    print("  1. Phase 1: Acquire data from multiple APIs")
    print("  2. Phase 2: Enrich data with matching and classification")
    print("  3. Individual component examples")

    input("\nPress Enter to begin Phase 1...")

    # Phase 1
    phase1_results = demo_phase1()

    input("\nPress Enter to begin Phase 2...")

    # Phase 2
    phase2_results = demo_phase2(phase1_results)

    input("\nPress Enter for individual component examples...")

    # Individual components
    demo_individual_components()

    print_header("DEMONSTRATION COMPLETE")

    print("Next steps:")
    print("  1. Review the generated data in data/raw/ and data/processed/")
    print("  2. Run tests with: pytest")
    print("  3. Connect real APIs by updating API adapter implementations")
    print("  4. Install transformers for full classification: pip install transformers torch")
    print("\nSee README.md for detailed documentation.")


if __name__ == "__main__":
    main()
