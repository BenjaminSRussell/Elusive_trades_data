"""
Ferguson API adapter.

This module provides an interface to fetch HVAC parts data from Ferguson's API.
"""

from typing import Dict, List, Any
import requests
import logging
from .base_api import BaseAPI

logger = logging.getLogger(__name__)


class FergusonAPI(BaseAPI):
    """
    API adapter for Ferguson parts data.

    Ferguson is a major distributor of HVAC parts and supplies. This adapter
    interfaces with their catalog API.
    """

    BASE_URL = "https://api.ferguson.com"  # Example URL - needs actual endpoint

    def __init__(self, output_dir: str = "data/raw", timeout: int = 30):
        """
        Initialize Ferguson API adapter.

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
        Search for a part by part number in Ferguson's catalog.

        Args:
            part_number: The part number to search for

        Returns:
            Dictionary containing the API response with part details
        """
        logger.info(f"Searching Ferguson API for part number: {part_number}")

        # TODO: Replace with actual Ferguson API endpoint
        mock_data = {
            "api": "ferguson",
            "part_number": part_number,
            "status": "found",
            "data": {
                "part_number": part_number,
                "description": "Capacitor 40/5 MFD 440V Round",
                "manufacturer": "Various",
                "in_stock": True,
                "price": 27.50,
                "availability": {
                    "warehouse": True,
                    "ship_time": "1-2 days",
                    "stock_quantity": 120
                },
                "specifications": {
                    "voltage": "440V",
                    "capacitance": "40/5 MFD",
                    "type": "Dual Run",
                    "shape": "Round"
                },
                "product_info": {
                    "upc": "123456789012",
                    "weight": "1.5 lbs",
                    "dimensions": "2.5\" x 5.5\""
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
        logger.info(f"Searching Ferguson API for model: {model_number}")

        mock_data = {
            "api": "ferguson",
            "model_number": model_number,
            "status": "found",
            "data": {
                "model": model_number,
                "manufacturer": "Goodman",
                "parts": [
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
        Get detailed information about a specific part from Ferguson.

        Args:
            part_id: The part number or internal ID

        Returns:
            Dictionary containing detailed part information
        """
        logger.info(f"Fetching Ferguson part details for: {part_id}")

        mock_data = {
            "api": "ferguson",
            "part_id": part_id,
            "status": "found",
            "data": {
                "part_number": part_id,
                "full_description": "Dual Run Capacitor, 40/5 MFD, 440V, Round",
                "category": "HVAC Controls & Accessories",
                "subcategory": "Capacitors",
                "brand": "Multiple Manufacturers",
                "specifications": {
                    "voltage": "440V",
                    "capacitance": "40/5 MFD",
                    "tolerance": "+/-6%",
                    "shape": "Round",
                    "mounting": "Universal Bracket"
                },
                "documents": [
                    {
                        "type": "spec_sheet",
                        "url": "https://example.com/spec.pdf"
                    },
                    {
                        "type": "installation_guide",
                        "url": "https://example.com/install.pdf"
                    }
                ],
                "related_products": [
                    {
                        "part_number": "CAP-45-5-440",
                        "description": "Similar capacitor 45/5 MFD"
                    }
                ]
            }
        }

        self.save_response(mock_data, f"details_{part_id}")
        return mock_data

    def get_available_endpoints(self) -> List[str]:
        """
        Get list of available Ferguson API endpoints.

        Returns:
            List of endpoint descriptions
        """
        return [
            "search_by_part_number(part_number) - Search for a specific part",
            "search_by_model(model_number) - Find parts for an equipment model",
            "get_part_details(part_id) - Get detailed part information"
        ]

    def __del__(self):
        """Close the session on cleanup."""
        if hasattr(self, 'session'):
            self.session.close()
