"""
Base API adapter for HVAC parts data acquisition.

This module defines the abstract interface that all API adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BaseAPI(ABC):
    """
    Abstract base class for all HVAC parts API adapters.

    Each API adapter must implement the required methods to provide
    a consistent interface for data acquisition.
    """

    def __init__(self, output_dir: str = "data/raw"):
        """
        Initialize the API adapter.

        Args:
            output_dir: Base directory for storing raw API responses
        """
        self.output_dir = Path(output_dir)
        self.api_name = self.__class__.__name__.replace("API", "").lower()
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create output directory for this API
        self.api_output_dir = self.output_dir / self.api_name / self.session_timestamp
        self.api_output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized {self.api_name} API adapter")
        logger.info(f"Output directory: {self.api_output_dir}")

    @abstractmethod
    def search_by_part_number(self, part_number: str) -> Dict[str, Any]:
        """
        Search for a specific part by its part number.

        Args:
            part_number: The part number to search for

        Returns:
            Dictionary containing the API response
        """
        pass

    @abstractmethod
    def search_by_model(self, model_number: str) -> Dict[str, Any]:
        """
        Search for parts by equipment model number.

        Args:
            model_number: The equipment model number

        Returns:
            Dictionary containing the API response
        """
        pass

    @abstractmethod
    def get_part_details(self, part_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific part.

        Args:
            part_id: The internal ID or part number

        Returns:
            Dictionary containing detailed part information
        """
        pass

    def save_response(self, data: Dict[str, Any], filename: str) -> Path:
        """
        Save API response to a JSON file.

        Args:
            data: The data to save
            filename: Name of the file (without extension)

        Returns:
            Path to the saved file
        """
        filepath = self.api_output_dir / f"{filename}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved response to {filepath}")
        return filepath

    def load_response(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load a previously saved API response.

        Args:
            filename: Name of the file (without extension)

        Returns:
            Loaded data or None if file doesn't exist
        """
        filepath = self.api_output_dir / f"{filename}.json"

        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"Loaded response from {filepath}")
        return data

    @abstractmethod
    def get_available_endpoints(self) -> List[str]:
        """
        Get a list of available API endpoints.

        Returns:
            List of endpoint descriptions
        """
        pass

    def get_api_info(self) -> Dict[str, Any]:
        """
        Get information about this API adapter.

        Returns:
            Dictionary containing API metadata
        """
        return {
            "name": self.api_name,
            "output_dir": str(self.api_output_dir),
            "session_timestamp": self.session_timestamp,
            "endpoints": self.get_available_endpoints()
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(output_dir={self.output_dir})"
