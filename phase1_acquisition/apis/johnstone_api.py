"""
Johnstone Supply API adapter.

This module provides an interface to fetch HVAC parts data from Johnstone Supply's API.
"""

from typing import Dict, List, Any
import requests
import logging
from .base_api import BaseAPI

logger = logging.getLogger(__name__)


class JohnstoneAPI(BaseAPI):
    """
    API adapter for Johnstone Supply parts data.

    Johnstone Supply is a major HVAC/R distributor. This adapter interfaces with their
    catalog to retrieve part availability and pricing information.
    """

    BASE_URL = "https://api.johnstonesupply.com"  # Example URL - needs actual endpoint

    def __init__(self, output_dir: str = "data/raw", timeout: int = 30):
        """
        Initialize Johnstone Supply API adapter.

        Args:
            output_dir: Directory for storing raw API responses
            timeout: Request timeout in seconds
        """
        super().__init__(output_dir)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HVAC-Parts-Search/1.0',
            'Accept': 'application/json'
        })

    def search_by_part_number(self, part_number: str) -> Dict[str, Any]:
        """
        Search for a part by part number in Johnstone's catalog.

        Args:
            part_number: The part number to search for

        Returns:
            Dictionary containing the API response with part details
        """
        logger.info(f"Searching Johnstone API for part number: {part_number}")

        # TODO: Replace with actual Johnstone API endpoint
        mock_data = {
            "api": "johnstone",
            "part_number": part_number,
            "status": "found",
            "data": {
                "part_number": part_number,
                "description": "Dual Round Capacitor 40+5 MFD 440V",
                "manufacturer": "Multiple Brands Available",
                "in_stock": True,
                "pricing": {
                    "retail": 29.99,
                    "contractor": 21.99
                },
                "availability": {
                    "warehouse": True,
                    "local_branch": True,
                    "quantity_available": 45
                },
                "brands": [
                    {
                        "name": "Goodman",
                        "part_number": "0131M00008P",
                        "price": 24.99
                    },
                    {
                        "name": "Carrier",
                        "part_number": "P291-4053RS",
                        "price": 26.99
                    },
                    {
                        "name": "Universal",
                        "part_number": "C4405R",
                        "price": 19.99
                    }
                ],
                "specifications": {
                    "voltage": "440V",
                    "capacitance": "40+5 MFD",
                    "type": "Dual Round"
                }
            }
        }

        self.save_response(mock_data, f"part_{part_number}")
        return mock_data

    def search_by_model(self, model_number: str) -> Dict[str, Any]:
        """
        Search for parts by equipment model number.

        Args:
            model_number: The equipment model number

        Returns:
            Dictionary containing list of parts for the model
        """
        logger.info(f"Searching Johnstone API for model: {model_number}")

        mock_data = {
            "api": "johnstone",
            "model_number": model_number,
            "status": "found",
            "data": {
                "model": model_number,
                "parts_list": [
                    {
                        "part_number": "0131M00008P",
                        "description": "Capacitor",
                        "price": 24.99,
                        "in_stock": True
                    }
                ]
            }
        }

        self.save_response(mock_data, f"model_{model_number}")
        return mock_data

    def get_part_details(self, part_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific part from Johnstone.

        Args:
            part_id: The part number or internal ID

        Returns:
            Dictionary containing detailed part information
        """
        logger.info(f"Fetching Johnstone part details for: {part_id}")

        mock_data = {
            "api": "johnstone",
            "part_id": part_id,
            "status": "found",
            "data": {
                "part_number": part_id,
                "description": "Dual Round Capacitor 40+5 MFD 440V",
                "category": "Electrical Components",
                "subcategory": "Capacitors",
                "multiple_brands": True,
                "available_brands": [
                    "Goodman",
                    "Carrier",
                    "Mars",
                    "Turbo"
                ],
                "specifications": {
                    "voltage": "440V",
                    "capacitance": "40+5 MFD",
                    "shape": "Round",
                    "diameter": "2.5 inches",
                    "height": "5.5 inches"
                },
                "technical_data": {
                    "temperature_range": "-40F to 185F",
                    "tolerance": "+/-6%",
                    "mounting": "Stud or Bracket"
                },
                "compatible_equipment": [
                    "Air Conditioners",
                    "Heat Pumps",
                    "Condensing Units"
                ]
            }
        }

        self.save_response(mock_data, f"details_{part_id}")
        return mock_data

    def search_by_category(self, category: str) -> Dict[str, Any]:
        """
        Browse parts by category.

        Args:
            category: The category name (e.g., "capacitors", "motors")

        Returns:
            Dictionary containing parts in the category
        """
        logger.info(f"Searching Johnstone API for category: {category}")

        mock_data = {
            "api": "johnstone",
            "category": category,
            "status": "found",
            "data": {
                "category_name": category,
                "subcategories": [
                    "Run Capacitors",
                    "Start Capacitors",
                    "Dual Capacitors"
                ],
                "featured_parts": []
            }
        }

        self.save_response(mock_data, f"category_{category}")
        return mock_data

    def get_available_endpoints(self) -> List[str]:
        """
        Get list of available Johnstone API endpoints.

        Returns:
            List of endpoint descriptions
        """
        return [
            "search_by_part_number(part_number) - Search for a specific part",
            "search_by_model(model_number) - Find parts for an equipment model",
            "get_part_details(part_id) - Get detailed part information",
            "search_by_category(category) - Browse parts by category"
        ]

    def __del__(self):
        """Close the session on cleanup."""
        if hasattr(self, 'session'):
            self.session.close()
