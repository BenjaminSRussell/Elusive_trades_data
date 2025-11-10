# Quick Start Guide - Fugitive Data Pipeline

This guide walks you through running the complete pipeline from scratch.

## Prerequisites

- Docker & Docker Compose installed
- Python 3.11+ installed
- 8GB+ RAM
- Internet connection (for scraping)

---

## Step 1: Initial Setup (5 minutes)

```bash
# Clone and navigate
cd Elusive_trades_data

# Install dependencies
make setup

# Edit .env with your settings
cp .env.example .env
nano .env  # Update passwords and credentials
```

**Important .env settings:**
```bash
POSTGRES_PASSWORD=your_secure_password
NEO4J_PASSWORD=your_secure_password
```

---

## Step 2: Start Infrastructure (2 minutes)

```bash
# Start all Docker services
make start

# Wait 30 seconds for services to initialize, then verify
docker ps

# You should see 6 containers running:
# - fugitive-kafka
# - fugitive-zookeeper
# - fugitive-postgres
# - fugitive-neo4j
# - fugitive-splash
# - fugitive-kafka-ui
```

**Access Web UIs:**
- Kafka UI: http://localhost:8080
- Neo4j Browser: http://localhost:7474 (user: neo4j, password: from .env)

---

## Step 3: Initialize Databases (1 minute)

```bash
# Create PostgreSQL schema
make db-migrate

# Create Neo4j constraints and indexes
make init-graph-schema

# Create Kafka topics
make create-topics

# Verify
make db-status
```

---

## Step 4: Scrape Real Data (10-30 minutes)

### Option A: Test Scraper (Recommended for first run)

```bash
# Run test spider against real HVAC sites
make scrape-test

# This will:
# - Scrape actual manufacturer websites (politely)
# - Respect robots.txt
# - Use rate limiting (3 second delays)
# - Extract PDFs and product data
# - Send to Kafka topics
```

### Option B: Targeted Manufacturers

```bash
# Scrape specific manufacturers
make scrape-goodman
make scrape-carrier
```

**Monitor scraping:**
```bash
# Watch Kafka messages
make logs

# Or check Kafka UI
open http://localhost:8080
```

---

## Step 5: Process Documents (Auto or Manual)

### Auto Mode (Background Processing)

```bash
# Start document processor (runs continuously)
make process-docs

# This will:
# - Consume from Kafka topics
# - Download PDFs
# - Extract text with PyMuPDF
# - Run OCR on scanned documents
# - Store in PostgreSQL
```

### Check Progress

```bash
# In another terminal, check database
make db-status

# You should see documents with nlp_status='pending'
```

---

## Step 6: Extract Knowledge with NLP (Auto or Manual)

### Manual Mode (Recommended for first run)

```bash
# Run NLP processor
make run-nlp

# This will:
# - Process all pending documents
# - Run custom NER (Part Numbers, Specs, Manufacturers)
# - Extract relationships (REPLACES, EQUIVALENT_TO, etc.)
# - Store entities and relationships in PostgreSQL
```

### Check Extraction Results

```bash
# Connect to PostgreSQL
make shell-postgres

# Then run:
SELECT entity_type, COUNT(*)
FROM entities
GROUP BY entity_type;

SELECT relation_type, COUNT(*)
FROM relationships
GROUP BY relation_type;

\q  # Exit
```

---

## Step 7: Populate Knowledge Graph (5 minutes)

```bash
# Transfer data from PostgreSQL to Neo4j
make populate-graph

# This creates:
# - Part nodes from extracted entities
# - Spec nodes from specifications
# - Equipment nodes
# - Manufacturer nodes
# - All relationships between them
```

### Verify Graph

```bash
# Open Neo4j shell
make shell-neo4j

# Run Cypher queries:
MATCH (n) RETURN labels(n), count(n);
MATCH ()-[r]->() RETURN type(r), count(r);

# Example: Find replacements
MATCH (p:Part {part_id: '0131M00008P'})-[:REPLACES]->(r:Part)
RETURN r.part_id, r.name;

:exit  # Exit
```

**Or use Neo4j Browser:**
```bash
open http://localhost:7474
# Login: neo4j / password (from .env)
```

---

## Step 8: Start the API (Instant)

```bash
# Start FastAPI server
make run-api

# API is now running at http://localhost:8000
```

### Test the API

```bash
# Open interactive API docs
open http://localhost:8000/docs

# Or use curl:
curl http://localhost:8000/health

# Look up a part (replace with actual part number from your data)
curl http://localhost:8000/lookup/part/0131M00008P

# Search by spec
curl "http://localhost:8000/lookup/spec/?type=MFD&value=40+5"

# Get replacement chain
curl http://localhost:8000/lookup/graph/replacements/0131M00008P?max_depth=5
```

---

## Step 9: Run Validation Tests

```bash
# Run integration tests
make test

# Run real-world scenario tests
make test-real

# Manual API test
python -c "
import httpx
response = httpx.get('http://localhost:8000/health')
print(response.json())
"
```

---

## Common Commands

```bash
# View all logs
make logs

# View specific service logs
docker compose -f docker/docker-compose.yml logs -f kafka

# Stop everything
make stop

# Restart everything
make restart

# Clean up
make clean

# Full reset (WARNING: deletes all data)
make stop
docker compose -f docker/docker-compose.yml down -v
make start
```

---

## Troubleshooting

### Services won't start

```bash
# Check Docker
docker ps
docker compose -f docker/docker-compose.yml ps

# Check logs
make logs

# Common issue: port conflicts
# Solution: Change ports in docker-compose.yml
```

### No data after scraping

```bash
# Check Kafka messages
open http://localhost:8080

# Check PostgreSQL
make shell-postgres
SELECT COUNT(*) FROM documents;
```

### NLP processing stuck

```bash
# Check NLP status
make db-status

# Reset NLP status to retry
make shell-postgres
UPDATE documents SET nlp_status = 'pending' WHERE nlp_status = 'failed';
```

### API returns 404 for all parts

```bash
# Graph might be empty
make shell-neo4j
MATCH (n:Part) RETURN count(n);

# If count is 0, run:
make populate-graph
```

---

## Performance Tips

1. **Scraping**: Start with `scrape-test` (limited to 10 products per page)
2. **Processing**: Increase `BATCH_SIZE` in .env for faster NLP
3. **Neo4j**: Allocate more memory in docker-compose.yml if you have >16GB RAM
4. **API**: Increase `API_WORKERS` in .env for more concurrent requests

---

## What's Next?

1. **Annotate Training Data**: See `docs/TRAINING_DATA.md`
2. **Fine-tune Models**: See `docs/MODEL_TRAINING.md`
3. **Production Deployment**: See `docs/DEPLOYMENT.md`
4. **Add More Spiders**: See `phase1_acquisition/scrapers/spiders/`

---

## Success Checklist

- [ ] All 6 Docker containers running
- [ ] PostgreSQL has documents
- [ ] Entities and relationships extracted
- [ ] Neo4j graph populated
- [ ] API responding at http://localhost:8000
- [ ] Can query parts via API
- [ ] Integration tests passing

**If all checked, congratulations! Your pipeline is operational! 🎉**
