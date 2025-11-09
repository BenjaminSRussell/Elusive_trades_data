"""
Scrapy pipelines for the Fugitive Data Pipeline.
Handles deduplication and publishing to Kafka.
"""

import json
import hashlib
import logging
from typing import Dict, Set
from kafka import KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)


class DeduplicationPipeline:
    """
    Deduplicates items based on content hash to prevent reprocessing.
    Uses an in-memory set (consider Redis for production).
    """

    def __init__(self):
        self.seen_hashes: Set[str] = set()

    def process_item(self, item, spider):
        """
        Calculate hash of item and check if already processed.
        """
        # Create a hash based on the source URL and key content
        if 'source_url' in item:
            hash_input = item['source_url']

            # Add PDF URL for PDF items
            if 'pdf_url' in item:
                hash_input += item['pdf_url']

            item_hash = hashlib.sha256(hash_input.encode()).hexdigest()

            if item_hash in self.seen_hashes:
                logger.debug(f"Duplicate item found: {item['source_url']}")
                raise DropItem(f"Duplicate item: {item_hash}")

            self.seen_hashes.add(item_hash)
            item['document_hash'] = item_hash

        return item


class KafkaProducerPipeline:
    """
    Publishes scraped items to appropriate Kafka topics.
    This is the "shock absorber" that decouples scraping from processing.
    """

    def __init__(self, bootstrap_servers: str, topics: Dict[str, str]):
        self.bootstrap_servers = bootstrap_servers
        self.topics = topics
        self.producer = None

    @classmethod
    def from_crawler(cls, crawler):
        """Create pipeline from crawler settings."""
        return cls(
            bootstrap_servers=crawler.settings.get('KAFKA_BOOTSTRAP_SERVERS'),
            topics={
                'pdf': crawler.settings.get('KAFKA_TOPIC_PDF_URLS'),
                'html': crawler.settings.get('KAFKA_TOPIC_HTML_CONTENT'),
                'forum': crawler.settings.get('KAFKA_TOPIC_FORUM_TEXT'),
            }
        )

    def open_spider(self, spider):
        """Initialize Kafka producer when spider opens."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',  # Wait for all replicas to acknowledge
                retries=3,
                max_in_flight_requests_per_connection=5
            )
            logger.info(f"Kafka producer initialized for {spider.name}")
        except KafkaError as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise

    def close_spider(self, spider):
        """Flush and close Kafka producer when spider closes."""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info(f"Kafka producer closed for {spider.name}")

    def process_item(self, item, spider):
        """
        Send item to appropriate Kafka topic based on document type.
        """
        if not self.producer:
            logger.error("Kafka producer not initialized")
            return item

        document_type = item.get('document_type')
        topic = self.topics.get(document_type)

        if not topic:
            logger.warning(f"No Kafka topic configured for type: {document_type}")
            return item

        # Convert item to dictionary
        item_dict = dict(item)

        # Send to Kafka
        try:
            future = self.producer.send(topic, value=item_dict)
            # Wait for send to complete (with timeout)
            record_metadata = future.get(timeout=10)

            logger.info(
                f"Item sent to Kafka: topic={record_metadata.topic}, "
                f"partition={record_metadata.partition}, offset={record_metadata.offset}"
            )

        except KafkaError as e:
            logger.error(f"Failed to send item to Kafka: {e}")
            # In production, consider a dead-letter queue or retry mechanism

        return item


class DropItem(Exception):
    """Exception to drop an item from the pipeline."""
    pass
