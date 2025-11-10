"""
Consumes NLP results from PostgreSQL and populates the Neo4j Knowledge Graph.
Reads entities and relationships from the Evidence Store and creates graph nodes/edges.
"""

import logging
from typing import Dict, List
from phase4_knowledge_graph.graph_db.neo4j_connection import Neo4jConnection
from phase4_knowledge_graph.schema.graph_schema import GraphSchema
from database.postgres.db_connection import db_pool, execute_query
from config.error_handling import retry_on_failure, log_exception, error_tracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphPopulator:
    """
    Populates Neo4j Knowledge Graph from PostgreSQL NLP results.
    """

    def __init__(self, neo4j_conn: Neo4jConnection = None):
        """
        Initialize graph populator.

        Args:
            neo4j_conn: Neo4j connection (creates new if None)
        """
        self.neo4j = neo4j_conn or Neo4jConnection()
        self.schema = GraphSchema(self.neo4j)

        self.stats = {
            'parts_created': 0,
            'specs_created': 0,
            'equipment_created': 0,
            'manufacturers_created': 0,
            'relationships_created': 0,
            'errors': 0
        }

    @retry_on_failure(max_retries=2, delay=1.0)
    def create_part_node(self, part_data: Dict) -> bool:
        """
        Create or update a Part node in the graph.

        Args:
            part_data: Dictionary with part information

        Returns:
            True if successful
        """
        try:
            query = """
            MERGE (p:Part {part_id: $part_id})
            SET p.name = $name,
                p.oem = $oem,
                p.source_doc_id = $source_doc_id,
                p.updated_at = timestamp()
            RETURN p.part_id AS part_id
            """

            result = self.neo4j.execute_query(query, {
                'part_id': part_data['part_id'],
                'name': part_data.get('name', ''),
                'oem': part_data.get('oem', False),
                'source_doc_id': part_data.get('source_doc_id')
            })

            if result:
                self.stats['parts_created'] += 1
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to create part node {part_data.get('part_id')}: {e}")
            error_tracker.record_error(
                component='graph_populator',
                error_type='part_creation',
                message=str(e),
                details=part_data
            )
            self.stats['errors'] += 1
            return False

    @retry_on_failure(max_retries=2, delay=1.0)
    def create_spec_node(self, spec_data: Dict) -> bool:
        """
        Create or update a Spec node in the graph.

        Args:
            spec_data: Dictionary with spec information

        Returns:
            True if successful
        """
        try:
            query = """
            MERGE (s:Spec {type: $type, value: $value})
            RETURN s.type AS type, s.value AS value
            """

            result = self.neo4j.execute_query(query, {
                'type': spec_data['type'],
                'value': spec_data['value']
            })

            if result:
                self.stats['specs_created'] += 1
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to create spec node: {e}")
            self.stats['errors'] += 1
            return False

    @retry_on_failure(max_retries=2, delay=1.0)
    def create_equipment_node(self, equipment_data: Dict) -> bool:
        """
        Create or update an Equipment node.

        Args:
            equipment_data: Dictionary with equipment information

        Returns:
            True if successful
        """
        try:
            query = """
            MERGE (e:Equipment {model: $model})
            SET e.type = $type,
                e.updated_at = timestamp()
            RETURN e.model AS model
            """

            result = self.neo4j.execute_query(query, {
                'model': equipment_data['model'],
                'type': equipment_data.get('type', 'Unknown')
            })

            if result:
                self.stats['equipment_created'] += 1
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to create equipment node: {e}")
            self.stats['errors'] += 1
            return False

    @retry_on_failure(max_retries=2, delay=1.0)
    def create_manufacturer_node(self, manufacturer_name: str) -> bool:
        """
        Create or update a Manufacturer node.

        Args:
            manufacturer_name: Manufacturer name

        Returns:
            True if successful
        """
        try:
            query = """
            MERGE (m:Manufacturer {name: $name})
            RETURN m.name AS name
            """

            result = self.neo4j.execute_query(query, {'name': manufacturer_name})

            if result:
                self.stats['manufacturers_created'] += 1
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to create manufacturer node: {e}")
            self.stats['errors'] += 1
            return False

    @retry_on_failure(max_retries=2, delay=1.0)
    def create_relationship(self, rel_data: Dict) -> bool:
        """
        Create a relationship between nodes.

        Args:
            rel_data: Dictionary with relationship data

        Returns:
            True if successful
        """
        try:
            rel_type = rel_data['relation_type']
            source_id = rel_data['source_id']
            target_id = rel_data['target_id']
            source_label = rel_data.get('source_label', 'Part')
            target_label = rel_data.get('target_label', 'Part')

            # Build dynamic query based on relationship type
            query = f"""
            MATCH (source:{source_label} {{part_id: $source_id}})
            MATCH (target:{target_label} {{part_id: $target_id}})
            MERGE (source)-[r:{rel_type}]->(target)
            SET r.confidence = $confidence,
                r.context = $context,
                r.is_tribal_knowledge = $is_tribal_knowledge,
                r.source_doc_id = $source_doc_id,
                r.created_at = timestamp()
            RETURN type(r) AS rel_type
            """

            result = self.neo4j.execute_query(query, {
                'source_id': source_id,
                'target_id': target_id,
                'confidence': rel_data.get('confidence', 0.5),
                'context': rel_data.get('context', ''),
                'is_tribal_knowledge': rel_data.get('is_tribal_knowledge', False),
                'source_doc_id': rel_data.get('source_doc_id')
            })

            if result:
                self.stats['relationships_created'] += 1
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            error_tracker.record_error(
                component='graph_populator',
                error_type='relationship_creation',
                message=str(e),
                details=rel_data
            )
            self.stats['errors'] += 1
            return False

    def populate_from_postgres(self, batch_size: int = 1000):
        """
        Populate graph from PostgreSQL Evidence Store.

        Args:
            batch_size: Number of records to process per batch
        """
        logger.info("Starting graph population from PostgreSQL...")

        try:
            # Step 1: Create Part nodes from entities
            logger.info("Creating Part nodes...")
            part_entities = execute_query("""
                SELECT DISTINCT
                    entity_text AS part_id,
                    entity_type,
                    document_id
                FROM entities
                WHERE entity_type = 'PART_NUMBER'
                LIMIT %s
            """, (batch_size,))

            for entity in part_entities:
                self.create_part_node({
                    'part_id': entity['part_id'],
                    'name': entity['part_id'],  # Could be enriched later
                    'oem': False,  # Determine from context
                    'source_doc_id': entity['document_id']
                })

            logger.info(f"✓ Created {self.stats['parts_created']} Part nodes")

            # Step 2: Create Manufacturer nodes
            logger.info("Creating Manufacturer nodes...")
            manufacturers = execute_query("""
                SELECT DISTINCT entity_text AS name
                FROM entities
                WHERE entity_type = 'MANUFACTURER'
                LIMIT %s
            """, (batch_size,))

            for mfr in manufacturers:
                self.create_manufacturer_node(mfr['name'])

            logger.info(f"✓ Created {self.stats['manufacturers_created']} Manufacturer nodes")

            # Step 3: Create Equipment nodes
            logger.info("Creating Equipment nodes...")
            equipment = execute_query("""
                SELECT DISTINCT entity_text AS model
                FROM entities
                WHERE entity_type = 'EQUIPMENT_MODEL'
                LIMIT %s
            """, (batch_size,))

            for equip in equipment:
                self.create_equipment_node({
                    'model': equip['model'],
                    'type': 'HVAC'  # Could be classified later
                })

            logger.info(f"✓ Created {self.stats['equipment_created']} Equipment nodes")

            # Step 4: Create Spec nodes and HAS_SPEC relationships
            logger.info("Creating Spec nodes...")
            spec_relations = execute_query("""
                SELECT
                    se.entity_text AS source_part,
                    te.entity_text AS spec_text
                FROM relationships r
                JOIN entities se ON r.source_entity_id = se.id
                JOIN entities te ON r.target_entity_id = te.id
                WHERE r.relation_type = 'HAS_SPEC'
                  AND se.entity_type = 'PART_NUMBER'
                  AND te.entity_type = 'SPECIFICATION'
                LIMIT %s
            """, (batch_size,))

            for rel in spec_relations:
                # Parse spec (simplified - would need better parsing)
                spec_text = rel['spec_text']
                self.create_spec_node({'type': 'SPEC', 'value': spec_text})

            logger.info(f"✓ Created {self.stats['specs_created']} Spec nodes")

            # Step 5: Create relationships from PostgreSQL
            logger.info("Creating relationships...")
            relationships = execute_query("""
                SELECT
                    se.entity_text AS source_id,
                    te.entity_text AS target_id,
                    se.entity_type AS source_label,
                    te.entity_type AS target_label,
                    r.relation_type,
                    r.confidence_score AS confidence,
                    r.context_text AS context,
                    r.is_tribal_knowledge,
                    r.document_id AS source_doc_id
                FROM relationships r
                JOIN entities se ON r.source_entity_id = se.id
                JOIN entities te ON r.target_entity_id = te.id
                WHERE r.relation_type IN ('REPLACES', 'EQUIVALENT_TO', 'COMPATIBLE_WITH', 'ADAPTER_REQUIRED')
                LIMIT %s
            """, (batch_size,))

            for rel in relationships:
                # Map PostgreSQL entity types to Neo4j labels
                label_map = {
                    'PART_NUMBER': 'Part',
                    'EQUIPMENT_MODEL': 'Equipment',
                    'ADAPTER': 'Part'
                }

                self.create_relationship({
                    'source_id': rel['source_id'],
                    'target_id': rel['target_id'],
                    'source_label': label_map.get(rel['source_label'], 'Part'),
                    'target_label': label_map.get(rel['target_label'], 'Part'),
                    'relation_type': rel['relation_type'],
                    'confidence': rel['confidence'] or 0.5,
                    'context': rel['context'] or '',
                    'is_tribal_knowledge': rel['is_tribal_knowledge'],
                    'source_doc_id': rel['source_doc_id']
                })

            logger.info(f"✓ Created {self.stats['relationships_created']} relationships")

            # Print summary
            self.print_stats()

        except Exception as e:
            logger.error(f"Graph population failed: {e}", exc_info=True)
            raise

    def print_stats(self):
        """Print population statistics."""
        logger.info("=" * 60)
        logger.info("Graph Population Statistics:")
        logger.info(f"  Parts Created: {self.stats['parts_created']}")
        logger.info(f"  Specs Created: {self.stats['specs_created']}")
        logger.info(f"  Equipment Created: {self.stats['equipment_created']}")
        logger.info(f"  Manufacturers Created: {self.stats['manufacturers_created']}")
        logger.info(f"  Relationships Created: {self.stats['relationships_created']}")
        logger.info(f"  Errors: {self.stats['errors']}")
        logger.info("=" * 60)


if __name__ == "__main__":
    try:
        with Neo4jConnection() as neo4j_conn:
            populator = GraphPopulator(neo4j_conn)
            populator.populate_from_postgres(batch_size=1000)
    except Exception as e:
        logger.error(f"Graph population failed: {e}")
