#!/bin/bash
#
# Quick Test Script - Tests the complete pipeline with sample data
# This script runs an end-to-end test without requiring real scraping
#

set -e  # Exit on error

echo "=========================================="
echo "  FUGITIVE PIPELINE - QUICK TEST"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if services are running
echo -e "${YELLOW}[1/7] Checking Docker services...${NC}"
if ! docker ps | grep -q fugitive-postgres; then
    echo -e "${RED}✗ Docker services not running!${NC}"
    echo "  Run: make start"
    exit 1
fi
echo -e "${GREEN}✓ Docker services running${NC}"
echo ""

# Generate sample training data
echo -e "${YELLOW}[2/7] Generating sample training data...${NC}"
python3 scripts/sample_data_generator.py
echo -e "${GREEN}✓ Sample data generated${NC}"
echo ""

# Insert sample documents into PostgreSQL
echo -e "${YELLOW}[3/7] Creating sample documents in PostgreSQL...${NC}"
docker exec -i fugitive-postgres psql -U fugitive_admin -d fugitive_evidence <<EOF
-- Insert sample documents
INSERT INTO documents (source_url, document_hash, raw_text_content, document_type)
VALUES
  ('https://example.com/goodman-motor.pdf', 'abc123hash', 'The Goodman 0131M00008P is a 1/3 HP condenser fan motor rated for 208-230V.', 'pdf'),
  ('https://example.com/icm-replacement.pdf', 'def456hash', 'The ICM282A replaces the 0131M00008P in most Goodman systems.', 'pdf'),
  ('https://example.com/capacitor-spec.pdf', 'ghi789hash', 'The Titan Pro TRCFD405 is a 40+5 MFD dual run capacitor rated for 440V.', 'pdf'),
  ('https://forum.hvac.com/post123', 'jkl012hash', 'Yeah, the Honeywell S9200U will work if you also get the mounting bracket adapter.', 'forum')
ON CONFLICT (document_hash) DO NOTHING;
EOF
echo -e "${GREEN}✓ Sample documents created${NC}"
echo ""

# Create sample entities
echo -e "${YELLOW}[4/7] Creating sample entities...${NC}"
docker exec -i fugitive-postgres psql -U fugitive_admin -d fugitive_evidence <<EOF
-- Insert sample entities
DO \$\$
DECLARE
    doc1_id INT;
    doc2_id INT;
    doc3_id INT;
BEGIN
    -- Get document IDs
    SELECT id INTO doc1_id FROM documents WHERE document_hash = 'abc123hash';
    SELECT id INTO doc2_id FROM documents WHERE document_hash = 'def456hash';
    SELECT id INTO doc3_id FROM documents WHERE document_hash = 'ghi789hash';

    -- Insert entities for doc 1
    INSERT INTO entities (document_id, entity_text, entity_type, start_char, end_char)
    VALUES
      (doc1_id, 'Goodman', 'MANUFACTURER', 4, 11),
      (doc1_id, '0131M00008P', 'PART_NUMBER', 12, 24),
      (doc1_id, '1/3 HP', 'SPECIFICATION', 30, 36),
      (doc1_id, '208-230V', 'SPECIFICATION', 66, 74);

    -- Insert entities for doc 2
    INSERT INTO entities (document_id, entity_text, entity_type, start_char, end_char)
    VALUES
      (doc2_id, 'ICM282A', 'PART_NUMBER', 4, 11),
      (doc2_id, '0131M00008P', 'PART_NUMBER', 25, 37);

    -- Insert entities for doc 3
    INSERT INTO entities (document_id, entity_text, entity_type, start_char, end_char)
    VALUES
      (doc3_id, 'Titan Pro', 'MANUFACTURER', 4, 13),
      (doc3_id, 'TRCFD405', 'PART_NUMBER', 14, 22),
      (doc3_id, '40+5 MFD', 'SPECIFICATION', 28, 36),
      (doc3_id, '440V', 'SPECIFICATION', 66, 70);
END \$\$;
EOF
echo -e "${GREEN}✓ Sample entities created${NC}"
echo ""

# Create sample relationships
echo -e "${YELLOW}[5/7] Creating sample relationships...${NC}"
docker exec -i fugitive-postgres psql -U fugitive_admin -d fugitive_evidence <<EOF
-- Insert sample relationships
DO \$\$
DECLARE
    icm_id INT;
    goodman_id INT;
BEGIN
    -- Get entity IDs
    SELECT id INTO icm_id FROM entities WHERE entity_text = 'ICM282A' LIMIT 1;
    SELECT id INTO goodman_id FROM entities WHERE entity_text = '0131M00008P' LIMIT 1;

    -- Insert REPLACES relationship
    INSERT INTO relationships (document_id, source_entity_id, target_entity_id, relation_type, confidence_score, context_text, is_tribal_knowledge)
    SELECT document_id, icm_id, goodman_id, 'REPLACES', 0.95, 'replaces', false
    FROM entities WHERE id = icm_id;
END \$\$;
EOF
echo -e "${GREEN}✓ Sample relationships created${NC}"
echo ""

# Populate Neo4j graph
echo -e "${YELLOW}[6/7] Populating Neo4j graph...${NC}"
docker exec -i fugitive-neo4j cypher-shell -u neo4j -p password <<EOF
// Create sample Part nodes
CREATE (:Part {part_id: '0131M00008P', name: 'Condenser Fan Motor', oem: true});
CREATE (:Part {part_id: 'ICM282A', name: 'Universal Replacement Motor', oem: false});
CREATE (:Part {part_id: 'TRCFD405', name: 'Dual Run Capacitor', oem: false});

// Create Manufacturer nodes
CREATE (:Manufacturer {name: 'Goodman'});
CREATE (:Manufacturer {name: 'Titan Pro'});

// Create Spec nodes
CREATE (:Spec {type: 'HP', value: '1/3'});
CREATE (:Spec {type: 'MFD', value: '40+5'});
CREATE (:Spec {type: 'Voltage', value: '440V'});

// Create relationships
MATCH (icm:Part {part_id: 'ICM282A'}), (goodman:Part {part_id: '0131M00008P'})
CREATE (icm)-[:REPLACES {confidence: 0.95}]->(goodman);

MATCH (cap:Part {part_id: 'TRCFD405'}), (spec:Spec {type: 'MFD', value: '40+5'})
CREATE (cap)-[:HAS_SPEC]->(spec);

MATCH (motor:Part {part_id: '0131M00008P'}), (mfr:Manufacturer {name: 'Goodman'})
CREATE (motor)-[:MANUFACTURED_BY]->(mfr);
EOF
echo -e "${GREEN}✓ Neo4j graph populated${NC}"
echo ""

# Test API
echo -e "${YELLOW}[7/7] Testing API endpoints...${NC}"

# Wait for API to be ready
sleep 2

# Test health
echo "  Testing /health..."
curl -s http://localhost:8000/health | python3 -m json.tool || echo "API not running. Start with: make run-api"

# Test part lookup
echo ""
echo "  Testing /lookup/part/0131M00008P..."
curl -s http://localhost:8000/lookup/part/0131M00008P | python3 -m json.tool || echo "Part not found or API not running"

echo ""
echo -e "${GREEN}✓ Tests complete${NC}"
echo ""

# Final status
echo "=========================================="
echo "  TEST SUMMARY"
echo "=========================================="
echo ""
echo "Database Stats:"
docker exec fugitive-postgres psql -U fugitive_admin -d fugitive_evidence -c "SELECT document_type, COUNT(*) FROM documents GROUP BY document_type;"
echo ""
docker exec fugitive-postgres psql -U fugitive_admin -d fugitive_evidence -c "SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type;"
echo ""

echo "Graph Stats:"
docker exec fugitive-neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC;"
echo ""

echo -e "${GREEN}=========================================="
echo "  🎉 QUICK TEST COMPLETE!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. View API docs: http://localhost:8000/docs"
echo "  2. Query Neo4j: http://localhost:7474"
echo "  3. Run full tests: make test-real"
echo ""
