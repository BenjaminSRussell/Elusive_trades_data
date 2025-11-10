"""
Lookup service that queries the Neo4j Knowledge Graph.
Business logic layer between API and database.
"""

import logging
from typing import List, Dict, Optional
from phase4_knowledge_graph.graph_db.neo4j_connection import (
    get_neo4j_connection, GraphQueryBuilder
)
from phase5_api.models.schemas import (
    PartInfo, SpecInfo, ReplacementInfo, EquipmentInfo,
    PartLookupResponse, ReplacementChainResponse, SpecSearchResponse
)
from config.error_handling import retry_on_failure, log_exception

logger = logging.getLogger(__name__)


class LookupService:
    """
    Service for querying parts, replacements, and specifications.
    """

    def __init__(self):
        self.neo4j = get_neo4j_connection()
        self.query_builder = GraphQueryBuilder()

    @retry_on_failure(max_retries=2, delay=0.5)
    @log_exception(logger)
    async def lookup_part(self, part_id: str) -> Optional[PartLookupResponse]:
        """
        Look up a part by ID and return all related information.

        Args:
            part_id: Part number to look up

        Returns:
            PartLookupResponse or None if not found
        """
        # Get part info
        part_query = """
        MATCH (p:Part {part_id: $part_id})
        OPTIONAL MATCH (p)-[:MANUFACTURED_BY]->(m:Manufacturer)
        RETURN p.part_id AS part_id,
               p.name AS name,
               p.oem AS oem,
               m.name AS manufacturer,
               p.source_doc_id AS source_doc_id
        """

        part_result = self.neo4j.execute_query(part_query, {'part_id': part_id})

        if not part_result:
            logger.warning(f"Part not found: {part_id}")
            return None

        part_data = part_result[0]

        # Get specifications
        specs_query = """
        MATCH (p:Part {part_id: $part_id})-[:HAS_SPEC]->(s:Spec)
        RETURN s.type AS type, s.value AS value
        """

        specs_result = self.neo4j.execute_query(specs_query, {'part_id': part_id})

        # Get direct replacements
        replacements_query = self.query_builder.find_replacements(part_id, max_depth=1)
        replacements_result = self.neo4j.execute_query(
            replacements_query,
            {'part_id': part_id}
        )

        # Get equivalent parts
        equivalent_query = self.query_builder.find_equivalent_parts(part_id)
        equivalent_result = self.neo4j.execute_query(
            equivalent_query,
            {'part_id': part_id}
        )

        # Get compatible equipment
        equipment_query = self.query_builder.find_compatible_equipment(part_id)
        equipment_result = self.neo4j.execute_query(
            equipment_query,
            {'part_id': part_id}
        )

        # Build response
        response = PartLookupResponse(
            part=PartInfo(
                part_id=part_data['part_id'],
                name=part_data.get('name', ''),
                oem=part_data.get('oem', False),
                manufacturer=part_data.get('manufacturer')
            ),
            specifications=[
                SpecInfo(type=s['type'], value=s['value'])
                for s in specs_result
            ],
            direct_replacements=[
                ReplacementInfo(
                    part_id=r['part_id'],
                    name=r.get('name', ''),
                    oem=r.get('oem', False),
                    confidence=r.get('confidence', 0.5),
                    degree=1
                )
                for r in replacements_result
            ],
            equivalent_parts=[
                ReplacementInfo(
                    part_id=e['part_id'],
                    name=e.get('name', ''),
                    oem=e.get('oem', False),
                    confidence=e.get('confidence', 0.5)
                )
                for e in equivalent_result
            ],
            compatible_equipment=[
                EquipmentInfo(
                    model=eq['model'],
                    type=eq.get('equipment_type'),
                    confidence=eq.get('confidence', 0.5)
                )
                for eq in equipment_result
            ],
            source_document_ids=[part_data.get('source_doc_id')] if part_data.get('source_doc_id') else []
        )

        return response

    @retry_on_failure(max_retries=2, delay=0.5)
    @log_exception(logger)
    async def get_replacement_chain(
        self,
        part_id: str,
        max_depth: int = 5
    ) -> Optional[ReplacementChainResponse]:
        """
        Get multi-degree replacement chain for a part.

        Args:
            part_id: Source part ID
            max_depth: Maximum traversal depth (1-5)

        Returns:
            ReplacementChainResponse or None
        """
        # Validate depth
        max_depth = min(max(max_depth, 1), 5)

        query = self.query_builder.find_replacements(part_id, max_depth=max_depth)
        result = self.neo4j.execute_query(query, {'part_id': part_id})

        if not result:
            return None

        # Group by degree
        by_degree: Dict[int, List[ReplacementInfo]] = {}
        tribal_count = 0

        for r in result:
            degree = r.get('degree', 1)

            if degree not in by_degree:
                by_degree[degree] = []

            by_degree[degree].append(ReplacementInfo(
                part_id=r['part_id'],
                name=r.get('name', ''),
                oem=r.get('oem', False),
                confidence=r.get('confidence', 0.5),
                degree=degree
            ))

        # Count tribal knowledge (from forum sources)
        tribal_query = """
        MATCH path = (p:Part {part_id: $part_id})-[r:REPLACES*1..%d]->(replacement:Part)
        WHERE any(rel IN relationships(path) WHERE rel.is_tribal_knowledge = true)
        RETURN count(DISTINCT replacement) AS count
        """ % max_depth

        tribal_result = self.neo4j.execute_query(tribal_query, {'part_id': part_id})
        if tribal_result:
            tribal_count = tribal_result[0].get('count', 0)

        return ReplacementChainResponse(
            source_part_id=part_id,
            replacements_by_degree=by_degree,
            total_replacements=len(result),
            max_degree=max(by_degree.keys()) if by_degree else 0,
            tribal_knowledge_count=tribal_count
        )

    @retry_on_failure(max_retries=2, delay=0.5)
    @log_exception(logger)
    async def search_by_spec(
        self,
        spec_type: str,
        spec_value: str
    ) -> SpecSearchResponse:
        """
        Search for parts by specification.

        Args:
            spec_type: Specification type (e.g., "MFD", "Voltage")
            spec_value: Specification value (e.g., "40+5", "440V")

        Returns:
            SpecSearchResponse
        """
        query = self.query_builder.find_by_spec(spec_type, spec_value)
        result = self.neo4j.execute_query(
            query,
            {'spec_type': spec_type, 'spec_value': spec_value}
        )

        matching_parts = [
            PartInfo(
                part_id=r['part_id'],
                name=r.get('name', ''),
                oem=r.get('oem', False)
            )
            for r in result
        ]

        return SpecSearchResponse(
            query_specs=[SpecInfo(type=spec_type, value=spec_value)],
            matching_parts=matching_parts,
            total_matches=len(matching_parts)
        )

    async def health_check(self) -> Dict[str, str]:
        """
        Check health of backend services.

        Returns:
            Dictionary with service statuses
        """
        services = {}

        # Check Neo4j
        try:
            self.neo4j.execute_query("RETURN 1")
            services['neo4j'] = 'connected'
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            services['neo4j'] = 'disconnected'

        # Check PostgreSQL
        try:
            from database.postgres.db_connection import execute_query
            execute_query("SELECT 1")
            services['postgres'] = 'connected'
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            services['postgres'] = 'disconnected'

        return services
