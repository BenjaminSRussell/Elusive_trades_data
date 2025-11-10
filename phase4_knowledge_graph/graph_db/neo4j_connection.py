"""
Neo4j connection and query utilities for the Knowledge Graph.
Provides connection pooling and context managers.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError
from config.error_handling import retry_on_failure, log_exception, CircuitBreaker
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Neo4jConnection:
    """
    Manages Neo4j database connections with connection pooling and error handling.
    """

    def __init__(
        self,
        uri: str = None,
        username: str = None,
        password: str = None
    ):
        """
        Initialize Neo4j connection.

        Args:
            uri: Neo4j connection URI (default: from env)
            username: Neo4j username (default: from env)
            password: Neo4j password (default: from env)
        """
        self.uri = uri or os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.username = username or os.getenv('NEO4J_USERNAME', 'neo4j')
        self.password = password or os.getenv('NEO4J_PASSWORD', 'password')

        self.driver: Optional[Driver] = None
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=30.0)

        self._connect()

    @retry_on_failure(max_retries=3, delay=2.0)
    @log_exception(logger)
    def _connect(self):
        """Establish connection to Neo4j."""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                max_connection_lifetime=3600,  # 1 hour
                max_connection_pool_size=50,
                connection_acquisition_timeout=30
            )

            # Verify connectivity
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")

        except AuthError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for Neo4j sessions.

        Usage:
            with neo4j_conn.get_session() as session:
                result = session.run("MATCH (n) RETURN n LIMIT 1")
        """
        if not self.driver:
            raise RuntimeError("Neo4j driver not initialized")

        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()

    @retry_on_failure(max_retries=2, delay=1.0)
    def execute_query(self, query: str, parameters: Dict = None) -> List[Dict]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result dictionaries

        Raises:
            Exception: If query fails after retries
        """
        parameters = parameters or {}

        def _run_query():
            with self.get_session() as session:
                result = session.run(query, parameters)
                return [dict(record) for record in result]

        try:
            return self.circuit_breaker.call(_run_query)
        except Exception as e:
            logger.error(f"Query failed: {query[:100]}... Error: {e}")
            raise

    def execute_write(self, query: str, parameters: Dict = None) -> Dict:
        """
        Execute a write query (CREATE, MERGE, etc.).

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            Query result summary
        """
        parameters = parameters or {}

        with self.get_session() as session:
            result = session.run(query, parameters)
            summary = result.consume()

            return {
                'nodes_created': summary.counters.nodes_created,
                'relationships_created': summary.counters.relationships_created,
                'properties_set': summary.counters.properties_set,
            }

    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class GraphQueryBuilder:
    """
    Helper class for building common Cypher queries.
    """

    @staticmethod
    def find_replacements(part_id: str, max_depth: int = 1) -> str:
        """
        Build query to find replacement parts.

        Args:
            part_id: Source part ID
            max_depth: Maximum traversal depth (1-5)

        Returns:
            Cypher query string
        """
        if max_depth == 1:
            # Direct replacements only
            return """
            MATCH (p:Part {part_id: $part_id})-[r:REPLACES]->(replacement:Part)
            RETURN replacement.part_id AS part_id,
                   replacement.name AS name,
                   replacement.oem AS oem,
                   r.confidence AS confidence
            ORDER BY r.confidence DESC
            """
        else:
            # Multi-degree replacements
            return f"""
            MATCH path = (p:Part {{part_id: $part_id}})-[:REPLACES*1..{max_depth}]->(replacement:Part)
            WITH replacement, length(path) AS degree
            RETURN DISTINCT replacement.part_id AS part_id,
                   replacement.name AS name,
                   replacement.oem AS oem,
                   degree
            ORDER BY degree ASC, replacement.part_id
            """

    @staticmethod
    def find_by_spec(spec_type: str, spec_value: str) -> str:
        """
        Build query to find parts by specification.

        Args:
            spec_type: Specification type (e.g., "MFD", "Voltage")
            spec_value: Specification value (e.g., "40+5", "440V")

        Returns:
            Cypher query string
        """
        return """
        MATCH (p:Part)-[:HAS_SPEC]->(s:Spec {type: $spec_type, value: $spec_value})
        RETURN p.part_id AS part_id,
               p.name AS name,
               p.oem AS oem
        ORDER BY p.oem DESC, p.part_id
        """

    @staticmethod
    def find_equivalent_parts(part_id: str) -> str:
        """
        Build query to find equivalent parts.

        Args:
            part_id: Source part ID

        Returns:
            Cypher query string
        """
        return """
        MATCH (p:Part {part_id: $part_id})-[r:EQUIVALENT_TO]-(equivalent:Part)
        RETURN equivalent.part_id AS part_id,
               equivalent.name AS name,
               equivalent.oem AS oem,
               r.confidence AS confidence
        ORDER BY r.confidence DESC
        """

    @staticmethod
    def find_compatible_equipment(part_id: str) -> str:
        """
        Build query to find compatible equipment.

        Args:
            part_id: Part ID

        Returns:
            Cypher query string
        """
        return """
        MATCH (p:Part {part_id: $part_id})-[r:COMPATIBLE_WITH]->(e:Equipment)
        RETURN e.model AS model,
               e.type AS equipment_type,
               r.confidence AS confidence,
               r.notes AS notes
        ORDER BY r.confidence DESC
        """

    @staticmethod
    def check_adapter_required(part_id: str, equipment_model: str) -> str:
        """
        Build query to check if adapter is required.

        Args:
            part_id: Part ID
            equipment_model: Equipment model

        Returns:
            Cypher query string
        """
        return """
        MATCH (p:Part {part_id: $part_id})-[r:ADAPTER_REQUIRED]->(a:Part)
        MATCH (p)-[:COMPATIBLE_WITH]->(e:Equipment {model: $equipment_model})
        RETURN a.part_id AS adapter_part_id,
               a.name AS adapter_name,
               r.context AS reason,
               r.confidence AS confidence
        """


# Global Neo4j connection instance
_neo4j_connection: Optional[Neo4jConnection] = None


def get_neo4j_connection() -> Neo4jConnection:
    """
    Get or create global Neo4j connection.

    Returns:
        Neo4jConnection instance
    """
    global _neo4j_connection

    if _neo4j_connection is None:
        _neo4j_connection = Neo4jConnection()

    return _neo4j_connection


if __name__ == "__main__":
    # Test connection
    logging.basicConfig(level=logging.INFO)

    try:
        with Neo4jConnection() as conn:
            result = conn.execute_query("RETURN 'Hello Neo4j!' AS message")
            logger.info(f"Test query result: {result}")
            logger.info("✓ Neo4j connection test successful!")
    except Exception as e:
        logger.error(f"✗ Neo4j connection test failed: {e}")
