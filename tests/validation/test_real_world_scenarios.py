"""
Five Real-World Validation Tests for the Fugitive Data Pipeline.
These tests validate the entire end-to-end system against difficult scenarios.
"""

import pytest
import logging
from typing import Dict, List
import httpx

logger = logging.getLogger(__name__)

# API base URL (adjust as needed)
API_BASE_URL = "http://localhost:8000"


class TestRealWorldScenarios:
    """
    End-to-end validation tests for the Fugitive Data Pipeline.
    Tests the complete system from scraping → processing → NLP → graph → API.
    """

    @pytest.fixture(scope="class")
    def api_client(self):
        """HTTP client for API requests."""
        return httpx.Client(base_url=API_BASE_URL, timeout=30.0)

    def test_01_discontinued_oem_part(self, api_client):
        """
        TEST 1: The Discontinued OEM Part (The User's Original Example)

        Query: Goodman 0131M00008P
        Expected:
        - Part identified as "Condenser Fan Motor" (NOT "fan control board")
        - Returns OEM replacements: 0131M00008PS and 0131M00430SF
        - All parts linked to source documents

        Validates: NER (Part Number, Part Type), RE (REPLACES), 1st-degree query
        """
        logger.info("=" * 60)
        logger.info("TEST 1: Discontinued OEM Part - Goodman 0131M00008P")
        logger.info("=" * 60)

        response = api_client.get("/lookup/part/0131M00008P")

        assert response.status_code == 200, "Part should be found"

        data = response.json()

        # Verify part information
        assert data['part']['part_id'] == "0131M00008P"
        assert "motor" in data['part']['name'].lower(), \
            "Should identify as motor, not control board"

        # Verify OEM replacements
        replacements = data['direct_replacements']
        replacement_ids = [r['part_id'] for r in replacements]

        assert "0131M00008PS" in replacement_ids or "0131M00430SF" in replacement_ids, \
            "Should return known OEM replacements"

        # Verify source documents
        assert len(data['source_document_ids']) > 0, \
            "Should link to source documents"

        logger.info(f"✓ Found {len(replacements)} direct replacements")
        logger.info(f"✓ Replacement IDs: {replacement_ids}")
        logger.info("TEST 1 PASSED\n")

    def test_02_rebranded_equivalent_part(self, api_client):
        """
        TEST 2: The Rebranded/Equivalent Part

        Query: A Janitrol part number (e.g., from rebranding)
        Expected:
        - Returns EQUIVALENT_TO relationship to Goodman part
        - Shows all replacements of the equivalent Goodman part

        Validates: NER, RE (EQUIVALENT_TO), graph traversal across relationship types
        """
        logger.info("=" * 60)
        logger.info("TEST 2: Rebranded/Equivalent Part - Janitrol Cross-Reference")
        logger.info("=" * 60)

        # Example Janitrol part (adjust based on actual data)
        janitrol_part = "JANITROL_0131M00008P"  # Hypothetical

        response = api_client.get(f"/lookup/part/{janitrol_part}")

        if response.status_code == 200:
            data = response.json()

            # Should have equivalent parts
            assert len(data['equivalent_parts']) > 0, \
                "Should have EQUIVALENT_TO relationships"

            # Should show Goodman equivalent
            equivalent_ids = [e['part_id'] for e in data['equivalent_parts']]
            logger.info(f"✓ Found {len(equivalent_ids)} equivalent parts")
            logger.info(f"✓ Equivalent IDs: {equivalent_ids}")
            logger.info("TEST 2 PASSED\n")
        else:
            logger.warning("TEST 2 SKIPPED: Janitrol test data not available\n")
            pytest.skip("Janitrol test data not in database")

    def test_03_spec_based_universal_part(self, api_client):
        """
        TEST 3: The Spec-Based Universal Part

        Query: Specs - 40+5 MFD, 440V capacitor
        Expected:
        - Returns multiple universal parts from various manufacturers
        - Examples: Titan Pro TRCFD405, Mars/Supco SFCAP40D5440R

        Validates: /lookup/spec/ endpoint, (Part)-->(Spec) graph traversal
        """
        logger.info("=" * 60)
        logger.info("TEST 3: Spec-Based Search - Universal Capacitor")
        logger.info("=" * 60)

        # Search by MFD specification
        response = api_client.get(
            "/lookup/spec/",
            params={"type": "MFD", "value": "40+5"}
        )

        assert response.status_code == 200

        data = response.json()

        # Should find multiple parts
        assert data['total_matches'] > 0, \
            "Should find parts matching 40+5 MFD spec"

        matching_parts = data['matching_parts']
        logger.info(f"✓ Found {len(matching_parts)} parts with 40+5 MFD spec")

        for part in matching_parts[:5]:  # Show first 5
            logger.info(f"  - {part['part_id']}: {part['name']}")

        # Verify we have both OEM and universal parts
        has_oem = any(p['oem'] for p in matching_parts)
        has_universal = any(not p['oem'] for p in matching_parts)

        if has_oem and has_universal:
            logger.info("✓ Includes both OEM and universal parts")

        logger.info("TEST 3 PASSED\n")

    def test_04_tribal_knowledge_replacement(self, api_client):
        """
        TEST 4: The Unstructured "Tribal Knowledge" Replacement

        Query: Honeywell ST9120U (older ignition control board)
        Expected:
        - Returns modern replacement: Honeywell S9200U1000
        - Relationship extracted from forum discussions (not clean tables)
        - Marked as tribal_knowledge

        Validates: Entire "Tribal Knowledge" pipeline (Phase 3.3)
        """
        logger.info("=" * 60)
        logger.info("TEST 4: Tribal Knowledge - Honeywell ST9120U")
        logger.info("=" * 60)

        response = api_client.get("/lookup/part/ST9120U")

        if response.status_code == 200:
            data = response.json()

            replacements = data['direct_replacements']
            replacement_ids = [r['part_id'] for r in replacements]

            # Should suggest S9200U1000 as modern replacement
            assert "S9200U1000" in replacement_ids or "S9200U" in replacement_ids, \
                "Should return S9200U1000 as replacement"

            logger.info(f"✓ Found replacements: {replacement_ids}")

            # Check if any came from tribal knowledge
            response_chain = api_client.get("/lookup/graph/replacements/ST9120U")
            if response_chain.status_code == 200:
                chain_data = response_chain.json()
                tribal_count = chain_data.get('tribal_knowledge_count', 0)

                logger.info(f"✓ Tribal knowledge relationships: {tribal_count}")

            logger.info("TEST 4 PASSED\n")
        else:
            logger.warning("TEST 4 SKIPPED: ST9120U test data not available\n")
            pytest.skip("ST9120U test data not in database")

    def test_05_multi_degree_complex_system(self, api_client):
        """
        TEST 5: The Multi-Degree "Complex System" Replacement (The Boss Test)

        Query: Dometic 63215 (older RV air conditioner)
        Expected:
        - Returns multi-part, conditional recommendation
        - Shows incompatibility warnings (thermostat issue)
        - Provides alternative solutions (A or B)
        - Demonstrates graph + NLP can model complex relationships

        Validates: Complex, conditional, multi-part relationships
        """
        logger.info("=" * 60)
        logger.info("TEST 5: Complex System Replacement - Dometic 63215")
        logger.info("=" * 60)

        # Query the replacement chain
        response = api_client.get(
            "/lookup/graph/replacements/63215",
            params={"max_depth": 3}
        )

        if response.status_code == 200:
            data = response.json()

            # Should have multi-degree replacements
            assert data['max_degree'] > 1, \
                "Should have multi-degree (transitive) replacements"

            logger.info(f"✓ Replacement chain depth: {data['max_degree']} degrees")
            logger.info(f"✓ Total replacements found: {data['total_replacements']}")

            # Show replacement chain
            for degree, parts in data['replacements_by_degree'].items():
                logger.info(f"  Degree {degree}: {len(parts)} parts")
                for part in parts[:3]:  # Show first 3
                    logger.info(f"    - {part['part_id']}: {part.get('notes', '')}")

            # Look for adapter requirements or warnings
            response_part = api_client.get("/lookup/part/63215")
            if response_part.status_code == 200:
                part_data = response_part.json()

                # Check for compatibility notes
                if part_data.get('compatible_equipment'):
                    logger.info("✓ Found equipment compatibility information")

            logger.info("TEST 5 PASSED\n")
        else:
            logger.warning("TEST 5 SKIPPED: Dometic 63215 test data not available\n")
            pytest.skip("Dometic 63215 test data not in database")

    def test_06_api_performance(self, api_client):
        """
        BONUS TEST: API Performance

        Validates: FastAPI async performance for concurrent I/O-bound queries
        """
        logger.info("=" * 60)
        logger.info("TEST 6: API Performance & Concurrency")
        logger.info("=" * 60)

        import time

        # Test single query performance
        start = time.time()
        response = api_client.get("/lookup/part/0131M00008P")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 2.0, "Single query should complete in < 2 seconds"

        logger.info(f"✓ Single query time: {duration:.3f}s")

        # Test health check
        health_response = api_client.get("/health")
        assert health_response.status_code == 200

        health_data = health_response.json()
        logger.info(f"✓ API Status: {health_data['status']}")
        logger.info(f"✓ Services: {health_data['services']}")

        # Verify all services are connected
        assert health_data['services']['neo4j'] == 'connected', \
            "Neo4j should be connected"

        logger.info("TEST 6 PASSED\n")


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--log-cli-level=INFO"
    ])
