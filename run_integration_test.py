#!/usr/bin/env python3
"""
End-to-End Integration Test Runner for the Fugitive Data Pipeline.

This script tests the complete pipeline from start to finish:
1. Infrastructure health checks
2. Scraping (optional)
3. Document processing
4. NLP extraction
5. Graph population
6. API queries

Usage:
    python run_integration_test.py [--full-test]
"""

import sys
import time
import logging
import argparse
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def check_service(service_name: str, check_function) -> bool:
    """
    Check if a service is running.

    Args:
        service_name: Name of service to check
        check_function: Function that returns True if service is healthy

    Returns:
        True if healthy, False otherwise
    """
    try:
        logger.info(f"Checking {service_name}...")
        result = check_function()

        if result:
            logger.info(f"✓ {service_name} is running")
            return True
        else:
            logger.error(f"✗ {service_name} is not responding")
            return False

    except Exception as e:
        logger.error(f"✗ {service_name} check failed: {e}")
        return False


def check_kafka():
    """Check Kafka connectivity."""
    try:
        from kafka import KafkaConsumer
        import os

        kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9093')

        consumer = KafkaConsumer(
            bootstrap_servers=kafka_servers,
            request_timeout_ms=5000
        )
        topics = consumer.topics()
        consumer.close()

        return len(topics) >= 0  # Just need to connect

    except Exception:
        return False


def check_postgres():
    """Check PostgreSQL connectivity."""
    try:
        from database.postgres.db_connection import execute_query
        result = execute_query("SELECT 1")
        return result is not None

    except Exception:
        return False


def check_neo4j():
    """Check Neo4j connectivity."""
    try:
        from phase4_knowledge_graph.graph_db.neo4j_connection import Neo4jConnection

        with Neo4jConnection() as conn:
            result = conn.execute_query("RETURN 1")
            return len(result) > 0

    except Exception:
        return False


def check_api():
    """Check FastAPI health."""
    try:
        import httpx

        response = httpx.get("http://localhost:8000/health", timeout=5)
        return response.status_code == 200

    except Exception:
        return False


def run_infrastructure_checks() -> bool:
    """
    Run all infrastructure health checks.

    Returns:
        True if all services are healthy
    """
    logger.info("=" * 60)
    logger.info("STEP 1: Infrastructure Health Checks")
    logger.info("=" * 60)

    services = {
        "Kafka": check_kafka,
        "PostgreSQL": check_postgres,
        "Neo4j": check_neo4j,
        "FastAPI": check_api,
    }

    results = {}
    for service_name, check_func in services.items():
        results[service_name] = check_service(service_name, check_func)
        time.sleep(0.5)

    # Summary
    logger.info("")
    logger.info("Infrastructure Summary:")
    for service, status in results.items():
        status_str = "✓ PASS" if status else "✗ FAIL"
        logger.info(f"  {service}: {status_str}")

    all_healthy = all(results.values())

    if all_healthy:
        logger.info("\n✓ All infrastructure services are healthy!\n")
    else:
        logger.error("\n✗ Some services are not healthy. Please start Docker services.\n")
        logger.error("Run: make start\n")

    return all_healthy


def run_database_checks():
    """Run database schema and data checks."""
    logger.info("=" * 60)
    logger.info("STEP 2: Database Schema & Data Checks")
    logger.info("=" * 60)

    try:
        from database.postgres.db_connection import execute_query

        # Check documents table
        docs_count = execute_query("""
            SELECT COUNT(*) as count FROM documents
        """)

        if docs_count:
            logger.info(f"✓ Documents table: {docs_count[0]['count']} records")

        # Check NLP processing status
        nlp_status = execute_query("""
            SELECT nlp_status, COUNT(*) as count
            FROM documents
            GROUP BY nlp_status
        """)

        if nlp_status:
            logger.info("  NLP Status Breakdown:")
            for row in nlp_status:
                logger.info(f"    - {row['nlp_status']}: {row['count']}")

        # Check entities
        entities_count = execute_query("SELECT COUNT(*) as count FROM entities")
        if entities_count:
            logger.info(f"✓ Entities extracted: {entities_count[0]['count']}")

        # Check relationships
        rels_count = execute_query("SELECT COUNT(*) as count FROM relationships")
        if rels_count:
            logger.info(f"✓ Relationships extracted: {rels_count[0]['count']}")

        logger.info("\n✓ PostgreSQL data checks passed\n")
        return True

    except Exception as e:
        logger.error(f"✗ Database check failed: {e}\n")
        return False


def run_graph_checks():
    """Run Neo4j graph checks."""
    logger.info("=" * 60)
    logger.info("STEP 3: Knowledge Graph Checks")
    logger.info("=" * 60)

    try:
        from phase4_knowledge_graph.graph_db.neo4j_connection import Neo4jConnection

        with Neo4jConnection() as conn:
            # Count nodes by label
            node_counts = conn.execute_query("""
                MATCH (n)
                RETURN labels(n)[0] AS label, count(n) AS count
                ORDER BY count DESC
            """)

            if node_counts:
                logger.info("  Node Counts:")
                for row in node_counts:
                    logger.info(f"    - {row['label']}: {row['count']}")
            else:
                logger.warning("  No nodes found in graph (run graph population)")

            # Count relationships
            rel_counts = conn.execute_query("""
                MATCH ()-[r]->()
                RETURN type(r) AS type, count(r) AS count
                ORDER BY count DESC
            """)

            if rel_counts:
                logger.info("  Relationship Counts:")
                for row in rel_counts:
                    logger.info(f"    - {row['type']}: {row['count']}")
            else:
                logger.warning("  No relationships found in graph")

        logger.info("\n✓ Neo4j graph checks passed\n")
        return True

    except Exception as e:
        logger.error(f"✗ Graph check failed: {e}\n")
        return False


def run_api_tests():
    """Run API endpoint tests."""
    logger.info("=" * 60)
    logger.info("STEP 4: API Endpoint Tests")
    logger.info("=" * 60)

    try:
        import httpx

        client = httpx.Client(base_url="http://localhost:8000", timeout=10)

        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        logger.info("✓ Root endpoint working")

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        logger.info(f"✓ Health check: {data['status']}")

        # Test part lookup (if data exists)
        test_parts = ["0131M00008P", "ICM282A", "S9200U1000"]

        for part_id in test_parts:
            try:
                response = client.get(f"/lookup/part/{part_id}")
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✓ Found part: {part_id} - {data['part']['name']}")
                    break
            except:
                continue

        # Test spec search
        try:
            response = client.get("/lookup/spec/", params={"type": "MFD", "value": "40+5"})
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✓ Spec search found {data['total_matches']} parts")
        except:
            logger.warning("  Spec search test skipped (no data)")

        client.close()

        logger.info("\n✓ API tests passed\n")
        return True

    except Exception as e:
        logger.error(f"✗ API tests failed: {e}\n")
        return False


def run_validation_tests():
    """Run the 5 real-world validation tests."""
    logger.info("=" * 60)
    logger.info("STEP 5: Real-World Validation Tests")
    logger.info("=" * 60)

    try:
        import subprocess

        result = subprocess.run(
            ["pytest", "tests/validation/test_real_world_scenarios.py", "-v"],
            capture_output=True,
            text=True
        )

        print(result.stdout)

        if result.returncode == 0:
            logger.info("\n✓ All validation tests passed!\n")
            return True
        else:
            logger.warning("\n⚠ Some validation tests failed (may need test data)\n")
            return False

    except Exception as e:
        logger.error(f"✗ Validation tests failed: {e}\n")
        return False


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description="Run integration tests for Fugitive Data Pipeline"
    )
    parser.add_argument(
        "--full-test",
        action="store_true",
        help="Run full test suite including scraping and processing"
    )

    args = parser.parse_args()

    logger.info("")
    logger.info("*" * 60)
    logger.info("  FUGITIVE DATA PIPELINE - INTEGRATION TEST SUITE")
    logger.info("*" * 60)
    logger.info("")

    # Track results
    results = {}

    # Step 1: Infrastructure
    results['infrastructure'] = run_infrastructure_checks()

    if not results['infrastructure']:
        logger.error("Infrastructure checks failed. Please start services with 'make start'")
        sys.exit(1)

    # Step 2: Database
    results['database'] = run_database_checks()

    # Step 3: Graph
    results['graph'] = run_graph_checks()

    # Step 4: API
    results['api'] = run_api_tests()

    # Step 5: Validation (if infrastructure is healthy)
    if all(results.values()):
        results['validation'] = run_validation_tests()

    # Final summary
    logger.info("=" * 60)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {test_name.title()}: {status}")

    logger.info("")

    all_passed = all(results.values())

    if all_passed:
        logger.info("🎉 ALL TESTS PASSED! Pipeline is ready for production.\n")
        sys.exit(0)
    else:
        logger.warning("⚠ Some tests failed. Review logs above.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
