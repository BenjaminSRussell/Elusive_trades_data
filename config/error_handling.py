"""
Centralized error handling and logging for the Fugitive Data Pipeline.
"""

import logging
import traceback
import functools
from typing import Callable, Any
from datetime import datetime


class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass


class ScrapingError(PipelineError):
    """Raised when scraping fails."""
    pass


class ProcessingError(PipelineError):
    """Raised when document processing fails."""
    pass


class NLPError(PipelineError):
    """Raised when NLP processing fails."""
    pass


class DatabaseError(PipelineError):
    """Raised when database operations fail."""
    pass


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry a function on failure with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import time

            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger = logging.getLogger(func.__module__)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger = logging.getLogger(func.__module__)
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )

            raise last_exception

        return wrapper
    return decorator


def safe_execute(func: Callable, *args, default=None, log_error: bool = True, **kwargs) -> Any:
    """
    Safely execute a function and return default value on error.

    Args:
        func: Function to execute
        *args: Positional arguments
        default: Default value to return on error
        log_error: Whether to log the error
        **kwargs: Keyword arguments

    Returns:
        Function result or default value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger = logging.getLogger(func.__module__)
            logger.error(f"Error in {func.__name__}: {e}")
        return default


def log_exception(logger: logging.Logger = None):
    """
    Decorator to log exceptions with full traceback.

    Args:
        logger: Logger instance (if None, uses function's module logger)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)

            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Exception in {func.__name__}: {e}\n"
                    f"Traceback:\n{traceback.format_exc()}"
                )
                raise

        return wrapper
    return decorator


class ErrorTracker:
    """
    Tracks errors across the pipeline for monitoring and debugging.
    """

    def __init__(self):
        self.errors = []
        self.error_counts = {}

    def record_error(self, component: str, error_type: str, message: str,
                     details: dict = None):
        """
        Record an error occurrence.

        Args:
            component: Which component failed (e.g., 'spider', 'pdf_processor')
            error_type: Type of error
            message: Error message
            details: Additional details
        """
        error_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'component': component,
            'error_type': error_type,
            'message': message,
            'details': details or {}
        }

        self.errors.append(error_record)

        # Track error counts
        key = f"{component}:{error_type}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1

    def get_error_summary(self) -> dict:
        """Get summary of errors."""
        return {
            'total_errors': len(self.errors),
            'error_counts': self.error_counts,
            'recent_errors': self.errors[-10:]  # Last 10 errors
        }

    def clear(self):
        """Clear all error records."""
        self.errors.clear()
        self.error_counts.clear()


# Global error tracker
error_tracker = ErrorTracker()


def validate_url(url: str) -> bool:
    """
    Validate that a URL is properly formed.

    Args:
        url: URL to validate

    Returns:
        True if valid, False otherwise
    """
    import re

    if not url or not isinstance(url, str):
        return False

    # Basic URL pattern
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    return bool(url_pattern.match(url))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to remove dangerous characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import re

    # Remove path separators and dangerous characters
    filename = re.sub(r'[/\\:*?"<>|]', '_', filename)

    # Limit length
    max_length = 255
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        name = name[:max_length - len(ext) - 1]
        filename = f"{name}.{ext}" if ext else name

    return filename


def validate_document_hash(hash_str: str) -> bool:
    """
    Validate that a hash string is a valid SHA256 hash.

    Args:
        hash_str: Hash string to validate

    Returns:
        True if valid SHA256, False otherwise
    """
    import re

    if not hash_str or not isinstance(hash_str, str):
        return False

    # SHA256 is 64 hex characters
    return bool(re.match(r'^[a-fA-F0-9]{64}$', hash_str))


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.
    """

    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half_open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call a function through the circuit breaker.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open
        """
        import time

        # Check if circuit should be half-open
        if self.state == 'open':
            if self.last_failure_time and \
               (time.time() - self.last_failure_time) > self.timeout:
                self.state = 'half_open'
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)

            # Success - reset if half-open
            if self.state == 'half_open':
                self.state = 'closed'
                self.failure_count = 0

            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = 'open'
                logging.getLogger(__name__).error(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )

            raise


# Setup logging configuration
def setup_logging(log_level: str = 'INFO', log_file: str = None):
    """
    Configure logging for the entire pipeline.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    """
    handlers = [logging.StreamHandler()]

    if log_file:
        from pathlib import Path
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        handlers=handlers
    )
