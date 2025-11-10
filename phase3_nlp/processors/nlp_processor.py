"""
NLP processor service that consumes documents from PostgreSQL,
runs NER and Relation Extraction, and stores results.
"""

import logging
import spacy
from typing import List, Dict
from pathlib import Path

from database.postgres.db_connection import db_pool, execute_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NLPProcessor:
    """
    Processes documents with NER and Relation Extraction.
    """

    def __init__(self, model_path: str = None):
        """
        Initialize NLP processor.

        Args:
            model_path: Path to custom trained model
        """
        if model_path and Path(model_path).exists():
            logger.info(f"Loading custom model from {model_path}")
            self.nlp = spacy.load(model_path)
        else:
            logger.warning("Custom model not found, using base model")
            self.nlp = spacy.load("en_core_web_trf")

        # Add relation extractor if not already in pipeline
        if "relation_extractor" not in self.nlp.pipe_names:
            from phase3_nlp.relation_extraction.relation_model import RelationExtractor
            self.nlp.add_pipe("relation_extractor")

        self.stats = {
            'processed': 0,
            'entities_extracted': 0,
            'relations_extracted': 0,
            'failed': 0
        }

    def process_pending_documents(self, batch_size: int = 100):
        """
        Process all documents with nlp_status='pending' from database.

        Args:
            batch_size: Number of documents to process in each batch
        """
        logger.info("Fetching pending documents from database...")

        query = """
            SELECT id, raw_text_content, document_type
            FROM documents
            WHERE nlp_status = 'pending'
              AND raw_text_content IS NOT NULL
              AND LENGTH(raw_text_content) > 100
            LIMIT %s
        """

        while True:
            documents = execute_query(query, (batch_size,))

            if not documents:
                logger.info("No more pending documents")
                break

            logger.info(f"Processing batch of {len(documents)} documents...")

            for doc_data in documents:
                try:
                    self.process_document(
                        doc_id=doc_data['id'],
                        text=doc_data['raw_text_content'],
                        doc_type=doc_data['document_type']
                    )
                except Exception as e:
                    logger.error(f"Failed to process document {doc_data['id']}: {e}")
                    self.mark_document_failed(doc_data['id'], str(e))
                    self.stats['failed'] += 1

        self.print_stats()

    def process_document(self, doc_id: int, text: str, doc_type: str):
        """
        Process a single document with NER and RE.

        Args:
            doc_id: Document ID
            text: Document text
            doc_type: Document type ('pdf', 'html', 'forum')
        """
        # Mark as processing
        execute_query(
            "UPDATE documents SET nlp_status = 'processing' WHERE id = %s",
            (doc_id,),
            fetch=False
        )

        # Run NLP pipeline
        doc = self.nlp(text)

        # Extract entities
        entities = self.extract_entities(doc)

        # Extract relations
        relations = self.extract_relations(doc)

        # Store results in database
        self.store_entities(doc_id, entities)
        self.store_relations(doc_id, relations, doc_type)

        # Mark as completed
        execute_query(
            """
            UPDATE documents
            SET nlp_status = 'completed', nlp_processed_at = NOW()
            WHERE id = %s
            """,
            (doc_id,),
            fetch=False
        )

        self.stats['processed'] += 1
        self.stats['entities_extracted'] += len(entities)
        self.stats['relations_extracted'] += len(relations)

        logger.info(
            f"✓ Processed doc {doc_id}: "
            f"{len(entities)} entities, {len(relations)} relations"
        )

    def extract_entities(self, doc) -> List[Dict]:
        """
        Extract entities from spaCy Doc.

        Args:
            doc: spaCy Doc object

        Returns:
            List of entity dictionaries
        """
        entities = []

        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start_char": ent.start_char,
                "end_char": ent.end_char,
            })

        return entities

    def extract_relations(self, doc) -> List[Dict]:
        """
        Extract relations from spaCy Doc.

        Args:
            doc: spaCy Doc object with relations

        Returns:
            List of relation dictionaries
        """
        if not hasattr(doc._, 'relations'):
            return []

        return doc._.relations

    def store_entities(self, doc_id: int, entities: List[Dict]):
        """
        Store entities in database.

        Args:
            doc_id: Document ID
            entities: List of entity dictionaries
        """
        if not entities:
            return

        # Prepare batch insert
        query = """
            INSERT INTO entities
            (document_id, entity_text, entity_type, start_char, end_char)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """

        entity_ids = []
        for ent in entities:
            result = execute_query(
                query,
                (doc_id, ent['text'], ent['label'], ent['start_char'], ent['end_char'])
            )
            if result:
                entity_ids.append(result[0]['id'])

        return entity_ids

    def store_relations(self, doc_id: int, relations: List[Dict], doc_type: str):
        """
        Store relations in database.

        Args:
            doc_id: Document ID
            relations: List of relation dictionaries
            doc_type: Document type
        """
        if not relations:
            return

        # For each relation, find the entity IDs and store
        for rel in relations:
            # Find source entity ID
            source_query = """
                SELECT id FROM entities
                WHERE document_id = %s AND entity_text = %s
                LIMIT 1
            """
            source_result = execute_query(
                source_query,
                (doc_id, rel['source'])
            )

            # Find target entity ID
            target_result = execute_query(
                source_query,
                (doc_id, rel['target'])
            )

            if source_result and target_result:
                # Insert relation
                insert_query = """
                    INSERT INTO relationships
                    (document_id, source_entity_id, target_entity_id,
                     relation_type, confidence_score, context_text, is_tribal_knowledge)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """

                execute_query(
                    insert_query,
                    (
                        doc_id,
                        source_result[0]['id'],
                        target_result[0]['id'],
                        rel['relation'],
                        rel.get('confidence', 0.8),
                        rel.get('context', ''),
                        doc_type == 'forum'  # Mark forum posts as tribal knowledge
                    ),
                    fetch=False
                )

    def mark_document_failed(self, doc_id: int, error_message: str):
        """
        Mark document as failed in database.

        Args:
            doc_id: Document ID
            error_message: Error message
        """
        execute_query(
            "UPDATE documents SET nlp_status = 'failed' WHERE id = %s",
            (doc_id,),
            fetch=False
        )

        execute_query(
            """
            INSERT INTO processing_errors
            (document_id, error_stage, error_message)
            VALUES (%s, %s, %s)
            """,
            (doc_id, 'nlp_processing', error_message),
            fetch=False
        )

    def print_stats(self):
        """Print processing statistics."""
        logger.info("=" * 60)
        logger.info("NLP Processor Statistics:")
        logger.info(f"  Documents Processed: {self.stats['processed']}")
        logger.info(f"  Entities Extracted: {self.stats['entities_extracted']}")
        logger.info(f"  Relations Extracted: {self.stats['relations_extracted']}")
        logger.info(f"  Failed: {self.stats['failed']}")
        logger.info("=" * 60)


if __name__ == "__main__":
    processor = NLPProcessor(model_path="phase3_nlp/models/custom_ner")
    processor.process_pending_documents()
