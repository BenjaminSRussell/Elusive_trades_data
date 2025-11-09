# Fugitive Data Pipeline

A comprehensive, distributed data pipeline for acquiring, processing, and extracting knowledge from HVAC/plumbing parts documentation across the web. This system transforms unstructured data into a queryable knowledge graph using advanced NLP techniques.

---

## 🏗️ Architecture Overview

The pipeline is organized into three main phases:

### **Phase 1: Data Acquisition**
Distributed web scraping with anti-bot evasion
- **Scrapy** framework with containerized spiders
- **Splash** for JavaScript-heavy sites
- Authenticated portal scraping
- **Apache Kafka** as the data event log (not a queue!)

### **Phase 2: Document Processing**
Converting raw documents into clean, structured text
- **PyMuPDF** for high-performance PDF extraction
- **OCR Pipeline** (OpenCV + Tesseract) for scanned documents
- **PostgreSQL** "Evidence Store" for processed documents
- Kafka consumer services

### **Phase 3: NLP Core**
Extracting structured knowledge from text
- **Custom NER** using spaCy transformers
- **Relation Extraction** for cross-references
- **Tribal Knowledge** extraction from forums
- Graph-ready relationship storage

---

## 📊 Data Flow

```
Web Sources → Scrapy Spiders → Kafka → Document Processors → PostgreSQL
                                                                    ↓
                                                              NLP Pipeline
                                                                    ↓
                                                    Knowledge Graph (Entities + Relations)
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- 8GB+ RAM recommended

### Setup

```bash
# Clone and navigate to repository
cd Elusive_trades_data

# Set up environment
make setup

# Edit .env with your credentials
nano .env

# Start all services
make start

# Initialize database
make db-migrate

# Create Kafka topics
make create-topics
```

### Verify Installation

```bash
# Check services are running
docker compose -f docker/docker-compose.yml ps

# Access Kafka UI
open http://localhost:8080

# Check database
make db-status
```

---

## 🕷️ Phase 1: Scraping

### Running Spiders

Each spider targets a specific manufacturer or distributor:

```bash
# Goodman (demonstrates Splash for JavaScript)
make scrape-goodman

# Carrier (demonstrates authentication)
make scrape-carrier

# Johnstone Supply (portal authentication)
make scrape-johnstone
```

### Spider Architecture

**Base Spider** (`base_spider.py`)
- Shared utilities for all spiders
- Splash request helpers
- PDF link extraction
- Specification parsing

**Target-Specific Spiders**
- `goodman_spider.py` - Dynamic content with Lua scripts
- `carrier_spider.py` - CSRF token handling
- `johnstone_spider.py` - Portal authentication

### Splash Lua Scripts

Located in `phase1_acquisition/splash_scripts/`:
- `click_tab_and_scroll.lua` - Tab clicking and lazy-loading
- `wait_for_element.lua` - Wait for specific elements

### Kafka Pipeline

Data flows through three topics:
- `pdf_urls` - PDF documents to process
- `html_content` - HTML product pages
- `forum_text` - Forum posts with tribal knowledge

**Why Kafka?**
- **Replayability**: Re-process all data with new models
- **Retention**: Configurable long-term storage
- **Throughput**: Millions of messages/second
- **Decoupling**: Scraping and processing are independent

---

## 📄 Phase 2: Document Processing

### PDF Extraction

**PyMuPDF (fitz)** - Superior performance and features:
- Native table extraction
- 5-10x faster than alternatives
- Built-in corruption repair with `pikepdf`

```python
from phase2_processing.pdf_processor.pdf_extractor import PDFExtractor

extractor = PDFExtractor()
result = extractor.extract_from_file('spec_sheet.pdf')

print(f"Extracted {len(result['text'])} characters")
print(f"Found {len(result['tables'])} tables")
```

### OCR Pipeline

For scanned documents, a multi-step preprocessing pipeline is critical:

1. **Image Extraction** (PyMuPDF)
2. **Deskewing** (OpenCV Hough transform)
3. **Binarization** (Adaptive thresholding)
4. **Noise Removal** (Morphological operations)
5. **OCR Execution** (Tesseract/OCRmyPDF)

```python
from phase2_processing.ocr_pipeline.ocr_service import OCRService

ocr = OCRService()
result = ocr.extract_text_from_pdf('scanned_spec.pdf')

print(f"Text: {result['text']}")
print(f"Confidence: {result['confidence']:.1f}%")
```

### Document Consumer

Runs continuously, consuming from Kafka and storing in PostgreSQL:

```bash
make process-docs
```

The consumer:
- Downloads PDFs from URLs
- Detects if OCR is required
- Deduplicates based on content hash
- Stores in Evidence Store

---

## 🧠 Phase 3: NLP Processing

### Custom Named Entity Recognition

Domain-specific entities:
- `PART_NUMBER` - e.g., "0131M00008P", "ICM282A"
- `MANUFACTURER` - e.g., "Goodman", "Carrier"
- `SPECIFICATION` - e.g., "40+5 MFD", "1/2 HP"
- `EQUIPMENT_MODEL` - e.g., "ARUF37C14"
- `ADAPTER` - e.g., "xyz adapter"

### Training Custom NER

```bash
# Train the model
make train-ner

# Or manually
python phase3_nlp/ner/train.py
```

Training data format (`training_data/sample_ner_training.json`):

```json
[
  {
    "text": "The Goodman 0131M00008P is a 1/3 HP fan motor.",
    "entities": [
      [4, 11, "MANUFACTURER"],
      [12, 24, "PART_NUMBER"],
      [30, 36, "SPECIFICATION"]
    ]
  }
]
```

### Relation Extraction

Extracts relationships between entities:
- `REPLACES` - Part A replaces Part B
- `EQUIVALENT_TO` - Parts are interchangeable
- `COMPATIBLE_WITH` - Part works with equipment
- `ADAPTER_REQUIRED` - Adapter needed for compatibility
- `HAS_SPEC` - Part has specification

### Running NLP Pipeline

```bash
make run-nlp
```

This processes all documents with `nlp_status='pending'` and:
1. Runs custom NER to find entities
2. Extracts relationships between entities
3. Stores results in PostgreSQL
4. Marks documents as processed

### Tribal Knowledge

Forum posts are specially flagged in the database:

```sql
SELECT * FROM tribal_knowledge_graph
WHERE relation_type = 'ADAPTER_REQUIRED'
ORDER BY confidence_score DESC;
```

This captures knowledge like:
> "Yeah, a Honeywell S9200 will work if you also get the 'xyz' adapter"

---

## 🗄️ Database Schema

### Core Tables

**documents** - Evidence Store
- `id` - Primary key
- `source_url` - Where document was found
- `document_hash` - SHA256 for deduplication
- `raw_text_content` - Extracted text
- `document_type` - pdf, html, or forum
- `nlp_status` - pending, processing, completed, failed
- `is_scanned` - Whether OCR was required

**entities** - Extracted entities
- Links to `documents`
- Stores entity text, type, position, confidence

**relationships** - Extracted relations
- Links source and target entities
- Relation type and confidence
- `is_tribal_knowledge` flag for forum data

### Useful Queries

```sql
-- Documents ready for NLP
SELECT * FROM documents_pending_nlp;

-- All cross-reference relationships
SELECT
    se.entity_text AS source_part,
    r.relation_type,
    te.entity_text AS target_part
FROM relationships r
JOIN entities se ON r.source_entity_id = se.id
JOIN entities te ON r.target_entity_id = te.id
WHERE r.relation_type IN ('REPLACES', 'EQUIVALENT_TO');

-- Forum-sourced tribal knowledge
SELECT * FROM tribal_knowledge_graph;
```

---

## 🐳 Docker Services

### Services

| Service | Port | Description |
|---------|------|-------------|
| Zookeeper | 2181 | Kafka coordination |
| Kafka | 9092/9093 | Event log |
| Kafka UI | 8080 | Web interface |
| Splash | 8050 | Headless browser |
| PostgreSQL | 5432 | Evidence Store |

### Commands

```bash
# View all logs
make logs

# PostgreSQL shell
make shell-postgres

# Kafka shell
make shell-kafka

# Restart everything
make restart
```

---

## 📁 Project Structure

```
Elusive_trades_data/
├── phase1_acquisition/          # Scrapy spiders and Kafka producers
│   ├── scrapers/
│   │   ├── spiders/             # Target-specific spiders
│   │   ├── settings.py          # Scrapy + Splash config
│   │   ├── pipelines.py         # Kafka producer pipeline
│   │   └── items.py             # Data models
│   └── splash_scripts/          # Lua scripts for Splash
│
├── phase2_processing/           # Document processing
│   ├── pdf_processor/           # PyMuPDF extraction
│   ├── ocr_pipeline/            # OpenCV + Tesseract
│   └── consumers/               # Kafka consumers
│
├── phase3_nlp/                  # NLP core
│   ├── ner/                     # Custom NER training
│   ├── relation_extraction/     # Relation extraction
│   ├── processors/              # NLP pipeline
│   └── training_data/           # Annotated data
│
├── database/
│   ├── migrations/              # SQL schema
│   └── postgres/                # Database utilities
│
├── docker/
│   ├── docker-compose.yml       # Service orchestration
│   └── Dockerfile.*             # Service containers
│
├── config/                      # Configuration
├── requirements/                # Dependencies by component
├── Makefile                     # Convenience commands
└── README.md                    # This file
```

---

## 🔧 Configuration

All configuration is in `.env`:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9093

# Credentials (DO NOT commit real credentials!)
JOHNSTONE_USERNAME=your_username
JOHNSTONE_PASSWORD=your_password
```

---

## 📈 Monitoring

### Kafka UI

Access at http://localhost:8080 to:
- View topic throughput
- Monitor consumer lag
- Inspect messages

### Database Status

```bash
make db-status
```

Shows document counts by type and processing status.

### Application Logs

All services log to stdout:

```bash
# All services
make logs

# Specific service
docker compose -f docker/docker-compose.yml logs -f kafka
```

---

## 🧪 Testing

```bash
# Run all tests
make test

# Test PDF extraction
python -m pytest tests/test_pdf_extractor.py -v

# Test OCR pipeline
python -m pytest tests/test_ocr_service.py -v

# Test NER
python -m pytest tests/test_ner.py -v
```

---

## 🔐 Security Notes

- **Never commit credentials** to version control
- Use `.env` for secrets (already in `.gitignore`)
- For production, use proper secrets management
- Authenticated scraping requires explicit authorization
- Respect `robots.txt` and terms of service

---

## 📚 Key Technologies

| Technology | Purpose | Why This Choice? |
|------------|---------|------------------|
| **Scrapy** | Web scraping | Industry standard, extensible |
| **Splash** | JavaScript rendering | Lightweight, scriptable |
| **Kafka** | Event log | Replayability for model updates |
| **PyMuPDF** | PDF extraction | Fastest, best table support |
| **OpenCV** | Image preprocessing | Critical for OCR accuracy |
| **Tesseract** | OCR | Open source, high accuracy |
| **spaCy** | NLP | Transformer support, custom components |
| **PostgreSQL** | Storage | Full-text search, JSONB support |

---

## 🎯 Next Steps

1. **Annotation**: Create training data using Prodigy or Label Studio
2. **Model Training**: Fine-tune NER and RE models on annotated data
3. **Knowledge Graph**: Export to Neo4j for graph queries
4. **API**: Build REST API for technician app
5. **Monitoring**: Add Prometheus + Grafana
6. **Scaling**: Deploy to Kubernetes for production

---

## 📄 License

This project is for educational and authorized research purposes.

---

## 🙏 Acknowledgments

Built using best practices from:
- spaCy NLP tutorials
- Scrapy documentation
- Apache Kafka documentation
- PostgreSQL performance guides

---

## 📧 Contact

For questions or issues, please open a GitHub issue.

---

**The Fugitive Data Pipeline** - Turning scattered parts data into structured knowledge.
