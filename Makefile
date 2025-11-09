# Fugitive Data Pipeline - Makefile
# Convenience commands for managing the pipeline

.PHONY: help setup start stop logs clean test

help:
	@echo "Fugitive Data Pipeline - Available Commands:"
	@echo ""
	@echo "  make setup          - Set up the environment and install dependencies"
	@echo "  make start          - Start all Docker services"
	@echo "  make stop           - Stop all Docker services"
	@echo "  make restart        - Restart all Docker services"
	@echo "  make logs           - View logs from all services"
	@echo "  make shell-kafka    - Open shell in Kafka container"
	@echo "  make shell-postgres - Open psql shell in PostgreSQL"
	@echo "  make clean          - Clean up temporary files and caches"
	@echo "  make test           - Run tests"
	@echo "  make scrape-goodman - Run Goodman spider"
	@echo "  make process-docs   - Start document processor"
	@echo "  make run-nlp        - Start NLP processor"
	@echo ""

setup:
	@echo "Setting up Fugitive Data Pipeline..."
	@cp .env.example .env
	@echo "Created .env file - please configure your credentials"
	@pip install -r requirements.txt
	@echo "Installed Python dependencies"
	@python -m spacy download en_core_web_trf
	@echo "Downloaded spaCy transformer model"
	@echo "Setup complete! Edit .env with your configuration, then run 'make start'"

start:
	@echo "Starting all services..."
	docker compose -f docker/docker-compose.yml up -d
	@echo "Services started! Access Kafka UI at http://localhost:8080"

stop:
	@echo "Stopping all services..."
	docker compose -f docker/docker-compose.yml down

restart: stop start

logs:
	docker compose -f docker/docker-compose.yml logs -f

shell-kafka:
	docker exec -it fugitive-kafka bash

shell-postgres:
	docker exec -it fugitive-postgres psql -U fugitive_admin -d fugitive_evidence

clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@rm -rf temp/*
	@echo "Cleanup complete"

test:
	@echo "Running tests..."
	pytest tests/ -v

# Spider commands
scrape-goodman:
	cd phase1_acquisition/scrapers && scrapy crawl goodman

scrape-carrier:
	cd phase1_acquisition/scrapers && scrapy crawl carrier

scrape-johnstone:
	cd phase1_acquisition/scrapers && scrapy crawl johnstone_supply

# Processing commands
process-docs:
	python phase2_processing/consumers/document_processor.py

run-nlp:
	python phase3_nlp/processors/nlp_processor.py

# Training commands
train-ner:
	python phase3_nlp/ner/train.py

# Kafka management
create-topics:
	docker exec -it fugitive-kafka kafka-topics --create --bootstrap-server localhost:9092 --topic pdf_urls --partitions 3 --replication-factor 1
	docker exec -it fugitive-kafka kafka-topics --create --bootstrap-server localhost:9092 --topic html_content --partitions 3 --replication-factor 1
	docker exec -it fugitive-kafka kafka-topics --create --bootstrap-server localhost:9092 --topic forum_text --partitions 3 --replication-factor 1

list-topics:
	docker exec -it fugitive-kafka kafka-topics --list --bootstrap-server localhost:9092

# Database management
db-migrate:
	docker exec -i fugitive-postgres psql -U fugitive_admin -d fugitive_evidence < database/migrations/001_initial_schema.sql

db-status:
	docker exec -it fugitive-postgres psql -U fugitive_admin -d fugitive_evidence -c "SELECT document_type, nlp_status, COUNT(*) FROM documents GROUP BY document_type, nlp_status;"
