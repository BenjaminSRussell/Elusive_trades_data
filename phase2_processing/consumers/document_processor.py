"""
Kafka consumer service for processing documents.
Consumes from pdf_urls and html_content topics, processes documents,
and stores results in PostgreSQL.
"""

import json
import logging
import hashlib
import tempfile
import requests
from pathlib import Path
from typing import Dict
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from phase2_processing.pdf_processor.pdf_extractor import PDFExtractor
from phase2_processing.ocr_pipeline.ocr_service import OCRService
from database.postgres.db_connection import db_pool, insert_document

# Load environment variables
import os
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Consumes documents from Kafka, processes them, and stores in PostgreSQL.
    """

    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.ocr_service = OCRService()

        # Kafka configuration
        self.kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9093')
        self.consumer_group = 'document_processors'

        self.stats = {
            'processed': 0,
            'failed': 0,
            'ocr_required': 0
        }

    def start_consuming(self, topics: list):
        """
        Start consuming from Kafka topics.

        Args:
            topics: List of topic names to consume from
        """
        try:
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=self.kafka_servers,
                group_id=self.consumer_group,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',  # For data replay capability
                enable_auto_commit=True,
                max_poll_records=10  # Process in small batches
            )

            logger.info(f"Started consuming from topics: {topics}")
            logger.info("Waiting for messages... (Press Ctrl+C to stop)")

            for message in consumer:
                try:
                    self.process_message(message)
                except Exception as e:
                    logger.error(f"Failed to process message: {e}")
                    self.stats['failed'] += 1

        except KafkaError as e:
            logger.error(f"Kafka consumer error: {e}")
            raise
        except KeyboardInterrupt:
            logger.info("Shutting down consumer...")
        finally:
            consumer.close()
            self.print_stats()

    def process_message(self, message):
        """
        Process a single Kafka message.

        Args:
            message: Kafka message object
        """
        topic = message.topic
        data = message.value

        logger.info(f"Processing message from {topic}: {data.get('source_url', 'unknown')}")

        if topic == 'pdf_urls':
            self.process_pdf(data)
        elif topic == 'html_content':
            self.process_html(data)
        elif topic == 'forum_text':
            self.process_forum(data)
        else:
            logger.warning(f"Unknown topic: {topic}")

    def process_pdf(self, data: Dict):
        """
        Process a PDF document.

        Args:
            data: Dictionary with pdf_url and metadata
        """
        pdf_url = data.get('pdf_url')
        source_url = data.get('source_url')

        if not pdf_url:
            logger.error("No pdf_url in message")
            return

        try:
            # Download PDF
            logger.info(f"Downloading PDF: {pdf_url}")
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()

            pdf_bytes = response.content

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = tmp.name

            # Extract text and tables
            result = self.pdf_extractor.extract_from_file(tmp_path)

            # Check if OCR is required
            if result.get('is_scanned', False) or len(result.get('text', '')) < 100:
                logger.info("Document appears to be scanned - running OCR")
                ocr_result = self.ocr_service.extract_text_from_pdf(tmp_path)
                result['text'] = ocr_result.get('text', result['text'])
                result['is_scanned'] = True
                self.stats['ocr_required'] += 1

            # Store in database
            document_id = insert_document(
                source_url=source_url or pdf_url,
                document_hash=result.get('document_hash', hashlib.sha256(pdf_bytes).hexdigest()),
                raw_text=result.get('text', ''),
                document_type='pdf',
                is_scanned=result.get('is_scanned', False),
                metadata={
                    **data.get('metadata', {}),
                    'pdf_url': pdf_url,
                    'page_count': result.get('page_count', 0),
                    'table_count': len(result.get('tables', [])),
                }
            )

            if document_id:
                logger.info(f"✓ Stored PDF in database: ID {document_id}")
                self.stats['processed'] += 1
            else:
                logger.info("Document already exists (duplicate)")

            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_url}: {e}")
            self.stats['failed'] += 1

    def process_html(self, data: Dict):
        """
        Process HTML content.

        Args:
            data: Dictionary with html_content and metadata
        """
        html_content = data.get('html_content')
        source_url = data.get('source_url')

        if not html_content:
            logger.error("No html_content in message")
            return

        try:
            # Extract text from HTML (simple approach - could use BeautifulSoup)
            from html import unescape
            import re

            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', html_content)
            # Unescape HTML entities
            text = unescape(text)
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()

            # Calculate hash
            doc_hash = hashlib.sha256(html_content.encode()).hexdigest()

            # Store in database
            document_id = insert_document(
                source_url=source_url,
                document_hash=doc_hash,
                raw_text=text,
                document_type='html',
                is_scanned=False,
                metadata=data.get('metadata', {})
            )

            if document_id:
                logger.info(f"✓ Stored HTML in database: ID {document_id}")
                self.stats['processed'] += 1
            else:
                logger.info("Document already exists (duplicate)")

        except Exception as e:
            logger.error(f"Failed to process HTML: {e}")
            self.stats['failed'] += 1

    def process_forum(self, data: Dict):
        """
        Process forum post text.

        Args:
            data: Dictionary with post_text and metadata
        """
        post_text = data.get('post_text') or data.get('content')
        source_url = data.get('source_url')

        if not post_text:
            logger.error("No post_text in message")
            return

        try:
            doc_hash = hashlib.sha256(post_text.encode()).hexdigest()

            # Store in database
            document_id = insert_document(
                source_url=source_url,
                document_hash=doc_hash,
                raw_text=post_text,
                document_type='forum',
                is_scanned=False,
                metadata={
                    **data.get('metadata', {}),
                    'is_tribal_knowledge': True
                }
            )

            if document_id:
                logger.info(f"✓ Stored forum post in database: ID {document_id}")
                self.stats['processed'] += 1
            else:
                logger.info("Document already exists (duplicate)")

        except Exception as e:
            logger.error(f"Failed to process forum post: {e}")
            self.stats['failed'] += 1

    def print_stats(self):
        """Print processing statistics."""
        logger.info("=" * 60)
        logger.info("Document Processor Statistics:")
        logger.info(f"  Processed: {self.stats['processed']}")
        logger.info(f"  Failed: {self.stats['failed']}")
        logger.info(f"  OCR Required: {self.stats['ocr_required']}")
        logger.info("=" * 60)


if __name__ == "__main__":
    processor = DocumentProcessor()

    # Consume from all document topics
    topics = ['pdf_urls', 'html_content', 'forum_text']

    processor.start_consuming(topics)
