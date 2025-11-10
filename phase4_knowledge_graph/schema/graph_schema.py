"""
Neo4j graph schema definitions and initialization.
Defines node labels, relationship types, and constraints.
"""

import logging
from typing import List
from phase4_knowledge_graph.graph_db.neo4j_connection import Neo4jConnection

logger = logging.getLogger(__name__)


class GraphSchema:
    """
    Manages the Knowledge Graph schema in Neo4j.
    """

    # Node Labels
    NODE_PART = "Part"
    NODE_SPEC = "Spec"
    NODE_EQUIPMENT = "Equipment"
    NODE_MANUFACTURER = "Manufacturer"
    NODE_ADAPTER = "Adapter"

    # Relationship Types
    REL_REPLACES = "REPLACES"
    REL_EQUIVALENT_TO = "EQUIVALENT_TO"
    REL_COMPATIBLE_WITH = "COMPATIBLE_WITH"
    REL_ADAPTER_REQUIRED = "ADAPTER_REQUIRED"
    REL_HAS_SPEC = "HAS_SPEC"
    REL_MANUFACTURED_BY = "MANUFACTURED_BY"
    REL_SOURCE_DOCUMENT = "SOURCE_DOCUMENT"

    def __init__(self, neo4j_conn: Neo4jConnection):
        """
        Initialize schema manager.

        Args:
            neo4j_conn: Neo4j connection instance
        """
        self.conn = neo4j_conn

    def create_constraints(self):
        """
        Create uniqueness constraints and indexes for optimal query performance.
        """
        constraints = [
            # Unique constraints (also create indexes)
            f"CREATE CONSTRAINT part_id_unique IF NOT EXISTS FOR (p:{self.NODE_PART}) REQUIRE p.part_id IS UNIQUE",
            f"CREATE CONSTRAINT equipment_model_unique IF NOT EXISTS FOR (e:{self.NODE_EQUIPMENT}) REQUIRE e.model IS UNIQUE",
            f"CREATE CONSTRAINT manufacturer_name_unique IF NOT EXISTS FOR (m:{self.NODE_MANUFACTURER}) REQUIRE m.name IS UNIQUE",

            # Composite constraint for Spec nodes
            f"CREATE CONSTRAINT spec_composite_unique IF NOT EXISTS FOR (s:{self.NODE_SPEC}) REQUIRE (s.type, s.value) IS UNIQUE",
        ]

        for constraint in constraints:
            try:
                self.conn.execute_write(constraint)
                logger.info(f"✓ Created constraint: {constraint[:60]}...")
            except Exception as e:
                # Constraint might already exist
                logger.debug(f"Constraint may already exist: {e}")

    def create_indexes(self):
        """
        Create additional indexes for query optimization.
        """
        indexes = [
            # Part indexes
            f"CREATE INDEX part_name_idx IF NOT EXISTS FOR (p:{self.NODE_PART}) ON (p.name)",
            f"CREATE INDEX part_oem_idx IF NOT EXISTS FOR (p:{self.NODE_PART}) ON (p.oem)",

            # Equipment indexes
            f"CREATE INDEX equipment_type_idx IF NOT EXISTS FOR (e:{self.NODE_EQUIPMENT}) ON (e.type)",

            # Spec indexes
            f"CREATE INDEX spec_type_idx IF NOT EXISTS FOR (s:{self.NODE_SPEC}) ON (s.type)",

            # Full-text search indexes
            f"CREATE FULLTEXT INDEX part_search_idx IF NOT EXISTS FOR (p:{self.NODE_PART}) ON EACH [p.part_id, p.name]",
        ]

        for index in indexes:
            try:
                self.conn.execute_write(index)
                logger.info(f"✓ Created index: {index[:60]}...")
            except Exception as e:
                logger.debug(f"Index may already exist: {e}")

    def initialize_schema(self):
        """
        Initialize the complete graph schema.
        """
        logger.info("Initializing Neo4j graph schema...")

        try:
            self.create_constraints()
            self.create_indexes()
            logger.info("✓ Graph schema initialization complete!")
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            raise

    def clear_database(self, confirm: bool = False):
        """
        Clear all nodes and relationships (USE WITH CAUTION!).

        Args:
            confirm: Must be True to actually clear
        """
        if not confirm:
            logger.warning("Database clear requires confirm=True")
            return

        logger.warning("Clearing entire Neo4j database...")

        try:
            # Delete all nodes and relationships
            self.conn.execute_write("MATCH (n) DETACH DELETE n")
            logger.info("✓ Database cleared")
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            raise

    def get_schema_info(self) -> dict:
        """
        Get information about the current schema.

        Returns:
            Dictionary with schema statistics
        """
        try:
            # Count nodes by label
            node_counts = self.conn.execute_query("""
                MATCH (n)
                RETURN labels(n)[0] AS label, count(n) AS count
                ORDER BY count DESC
            """)

            # Count relationships by type
            rel_counts = self.conn.execute_query("""
                MATCH ()-[r]->()
                RETURN type(r) AS type, count(r) AS count
                ORDER BY count DESC
            """)

            # Get constraints
            constraints = self.conn.execute_query("SHOW CONSTRAINTS")

            # Get indexes
            indexes = self.conn.execute_query("SHOW INDEXES")

            return {
                'node_counts': node_counts,
                'relationship_counts': rel_counts,
                'constraints': len(constraints),
                'indexes': len(indexes)
            }

        except Exception as e:
            logger.error(f"Failed to get schema info: {e}")
            return {}


# Example Cypher queries for reference
EXAMPLE_QUERIES = {
    "find_direct_replacements": """
        MATCH (p:Part {part_id: '0131M00008P'})-[:REPLACES]->(r:Part)
        RETURN r.part_id, r.name
    """,

    "find_multi_degree_replacements": """
        MATCH path = (p:Part {part_id: '0131M00008P'})-[:REPLACES*1..5]->(r:Part)
        RETURN r.part_id, r.name, length(path) AS degree
        ORDER BY degree ASC
    """,

    "find_by_spec": """
        MATCH (p:Part)-[:HAS_SPEC]->(s:Spec {type: 'MFD', value: '40+5'})
        RETURN p.part_id, p.name
    """,

    "find_equivalent_parts": """
        MATCH (p:Part {part_id: 'JANITROL_ABC123'})-[:EQUIVALENT_TO]-(e:Part)
        RETURN e.part_id, e.name
    """,

    "check_adapter_required": """
        MATCH (p:Part {part_id: 'S9200U1000'})-[r:ADAPTER_REQUIRED]->(a:Part)
        RETURN a.part_id, a.name, r.context
    """,

    "tribal_knowledge_query": """
        MATCH (p:Part)-[r:ADAPTER_REQUIRED|COMPATIBLE_WITH]->(target)
        WHERE r.is_tribal_knowledge = true
        RETURN p.part_id, type(r) AS relationship, target.part_id OR target.model AS target,
               r.context, r.source_url
        ORDER BY r.confidence DESC
    """,
}


if __name__ == "__main__":
    # Test schema initialization
    logging.basicConfig(level=logging.INFO)

    from phase4_knowledge_graph.graph_db.neo4j_connection import Neo4jConnection

    try:
        with Neo4jConnection() as conn:
            schema = GraphSchema(conn)
            schema.initialize_schema()

            # Print schema info
            info = schema.get_schema_info()
            print("\nGraph Schema Information:")
            print(f"  Constraints: {info.get('constraints', 0)}")
            print(f"  Indexes: {info.get('indexes', 0)}")
            print(f"\n  Node Counts: {info.get('node_counts', [])}")
            print(f"\n  Relationship Counts: {info.get('relationship_counts', [])}")

    except Exception as e:
        logger.error(f"Schema test failed: {e}")
