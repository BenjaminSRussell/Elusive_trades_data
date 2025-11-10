"""
Database connection utilities for the Fugitive Data Pipeline.
Provides connection pooling and context managers for PostgreSQL.
"""

import os
import logging
from contextlib import contextmanager
from typing import Optional

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DatabasePool:
    """Singleton connection pool for PostgreSQL."""

    _instance: Optional['DatabasePool'] = None
    _pool: Optional[pool.ThreadedConnectionPool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._pool is None:
            self._initialize_pool()

    def _initialize_pool(self):
        """Initialize the connection pool."""
        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=5,
                maxconn=20,
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=os.getenv('POSTGRES_PORT', '5432'),
                database=os.getenv('POSTGRES_DB', 'fugitive_evidence'),
                user=os.getenv('POSTGRES_USER', 'fugitive_admin'),
                password=os.getenv('POSTGRES_PASSWORD', 'changeme_in_production')
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Context manager for getting a database connection from the pool.

        Usage:
            with db_pool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM documents")
        """
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self, cursor_factory=RealDictCursor):
        """
        Context manager for getting a cursor directly.

        Usage:
            with db_pool.get_cursor() as cur:
                cur.execute("SELECT * FROM documents")
                results = cur.fetchall()
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
            finally:
                cursor.close()

    def close_all(self):
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            logger.info("All database connections closed")


# Global pool instance
db_pool = DatabasePool()


# Convenience functions
def execute_query(query: str, params: tuple = None, fetch: bool = True):
    """
    Execute a query and optionally fetch results.

    Args:
        query: SQL query string
        params: Query parameters (for parameterized queries)
        fetch: If True, return fetched results; if False, return None

    Returns:
        List of dict rows if fetch=True, None otherwise
    """
    with db_pool.get_cursor() as cur:
        cur.execute(query, params)
        if fetch:
            return cur.fetchall()
        return None


def execute_many(query: str, params_list: list):
    """
    Execute a query multiple times with different parameters.

    Args:
        query: SQL query string
        params_list: List of tuples containing parameters for each execution
    """
    with db_pool.get_cursor() as cur:
        cur.executemany(query, params_list)


def insert_document(source_url: str, document_hash: str, raw_text: str,
                   document_type: str, is_scanned: bool = False,
                   metadata: dict = None) -> int:
    """
    Insert a new document into the Evidence Store.

    Args:
        source_url: URL where the document was found
        document_hash: SHA256 hash of the document
        raw_text: Extracted text content
        document_type: Type of document ('pdf', 'html', 'forum')
        is_scanned: Whether OCR was required
        metadata: Additional metadata as JSON

    Returns:
        The document ID of the inserted row
    """
    import json

    query = """
        INSERT INTO documents
        (source_url, document_hash, raw_text_content, document_type, is_scanned, metadata)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (document_hash) DO NOTHING
        RETURNING id
    """

    with db_pool.get_cursor() as cur:
        cur.execute(query, (
            source_url,
            document_hash,
            raw_text,
            document_type,
            is_scanned,
            json.dumps(metadata) if metadata else None
        ))
        result = cur.fetchone()
        return result['id'] if result else None


if __name__ == "__main__":
    # Test connection
    logging.basicConfig(level=logging.INFO)

    try:
        result = execute_query("SELECT version()")
        logger.info(f"PostgreSQL version: {result[0]['version']}")
        logger.info("Database connection test successful!")
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
