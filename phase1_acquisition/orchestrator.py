"""
API Orchestrator for Phase 1 data acquisition.

This module coordinates data collection from multiple HVAC parts APIs.
"""

from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
import json
from datetime import datetime

from .apis.goodman_api import GoodmanAPI
from .apis.carrier_api import CarrierAPI
from .apis.johnstone_api import JohnstoneAPI
from .apis.ferguson_api import FergusonAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class APIOrchestrator:
    """
    Orchestrates data collection from multiple HVAC parts APIs.

    This class manages multiple API adapters and provides a unified interface
    for searching parts across all available data sources.
    """

    def __init__(self, output_dir: str = "data/raw"):
        """
        Initialize the orchestrator with all available API adapters.

        Args:
            output_dir: Base directory for storing raw API responses
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize all API adapters
        self.apis = {
            'goodman': GoodmanAPI(output_dir),
            'carrier': CarrierAPI(output_dir),
            'johnstone': JohnstoneAPI(output_dir),
            'ferguson': FergusonAPI(output_dir)
        }

        logger.info(f"Initialized orchestrator with {len(self.apis)} API adapters")

    def search_all_apis(self, part_number: str) -> Dict[str, Any]:
        """
        Search for a part number across all APIs.

        Args:
            part_number: The part number to search for

        Returns:
            Dictionary containing results from all APIs
        """
        logger.info(f"Searching all APIs for part number: {part_number}")

        results = {
            "part_number": part_number,
            "timestamp": datetime.now().isoformat(),
            "apis_queried": list(self.apis.keys()),
            "results": {}
        }

        for api_name, api_adapter in self.apis.items():
            try:
                logger.info(f"Querying {api_name} API...")
                result = api_adapter.search_by_part_number(part_number)
                results["results"][api_name] = {
                    "status": "success",
                    "data": result
                }
            except Exception as e:
                logger.error(f"Error querying {api_name} API: {e}")
                results["results"][api_name] = {
                    "status": "error",
                    "error": str(e)
                }

        # Save consolidated results
        self._save_consolidated_results(results, f"search_all_{part_number}")

        return results

    def get_part_details_from_all(self, part_number: str) -> Dict[str, Any]:
        """
        Get detailed part information from all APIs.

        Args:
            part_number: The part number to get details for

        Returns:
            Dictionary containing detailed results from all APIs
        """
        logger.info(f"Fetching details from all APIs for: {part_number}")

        results = {
            "part_number": part_number,
            "timestamp": datetime.now().isoformat(),
            "apis_queried": list(self.apis.keys()),
            "details": {}
        }

        for api_name, api_adapter in self.apis.items():
            try:
                logger.info(f"Fetching details from {api_name} API...")
                result = api_adapter.get_part_details(part_number)
                results["details"][api_name] = {
                    "status": "success",
                    "data": result
                }
            except Exception as e:
                logger.error(f"Error fetching details from {api_name} API: {e}")
                results["details"][api_name] = {
                    "status": "error",
                    "error": str(e)
                }

        # Save consolidated results
        self._save_consolidated_results(results, f"details_all_{part_number}")

        return results

    def search_by_model_all_apis(self, model_number: str) -> Dict[str, Any]:
        """
        Search for an equipment model across all APIs.

        Args:
            model_number: The equipment model number

        Returns:
            Dictionary containing results from all APIs
        """
        logger.info(f"Searching all APIs for model: {model_number}")

        results = {
            "model_number": model_number,
            "timestamp": datetime.now().isoformat(),
            "apis_queried": list(self.apis.keys()),
            "results": {}
        }

        for api_name, api_adapter in self.apis.items():
            try:
                logger.info(f"Querying {api_name} API for model...")
                result = api_adapter.search_by_model(model_number)
                results["results"][api_name] = {
                    "status": "success",
                    "data": result
                }
            except Exception as e:
                logger.error(f"Error querying {api_name} API: {e}")
                results["results"][api_name] = {
                    "status": "error",
                    "error": str(e)
                }

        # Save consolidated results
        self._save_consolidated_results(results, f"model_all_{model_number}")

        return results

    def search_specific_apis(self, part_number: str, api_names: List[str]) -> Dict[str, Any]:
        """
        Search for a part number in specific APIs only.

        Args:
            part_number: The part number to search for
            api_names: List of API names to query (e.g., ['goodman', 'carrier'])

        Returns:
            Dictionary containing results from specified APIs
        """
        logger.info(f"Searching specific APIs {api_names} for: {part_number}")

        results = {
            "part_number": part_number,
            "timestamp": datetime.now().isoformat(),
            "apis_queried": api_names,
            "results": {}
        }

        for api_name in api_names:
            if api_name not in self.apis:
                logger.warning(f"API '{api_name}' not found, skipping")
                results["results"][api_name] = {
                    "status": "error",
                    "error": f"API '{api_name}' not available"
                }
                continue

            try:
                logger.info(f"Querying {api_name} API...")
                result = self.apis[api_name].search_by_part_number(part_number)
                results["results"][api_name] = {
                    "status": "success",
                    "data": result
                }
            except Exception as e:
                logger.error(f"Error querying {api_name} API: {e}")
                results["results"][api_name] = {
                    "status": "error",
                    "error": str(e)
                }

        return results

    def get_api_info(self) -> Dict[str, Any]:
        """
        Get information about all configured APIs.

        Returns:
            Dictionary containing info for each API adapter
        """
        info = {
            "total_apis": len(self.apis),
            "apis": {}
        }

        for api_name, api_adapter in self.apis.items():
            info["apis"][api_name] = api_adapter.get_api_info()

        return info

    def add_api(self, name: str, api_adapter):
        """
        Add a new API adapter to the orchestrator.

        Args:
            name: Name for the API
            api_adapter: Instance of an API adapter (must inherit from BaseAPI)

        Example:
            >>> from apis.grainger_api import GraingerAPI
            >>> orchestrator = APIOrchestrator()
            >>> orchestrator.add_api('grainger', GraingerAPI())
        """
        self.apis[name] = api_adapter
        logger.info(f"Added new API adapter: {name}")

    def _save_consolidated_results(self, data: Dict[str, Any], filename: str) -> Path:
        """
        Save consolidated results from multiple APIs.

        Args:
            data: The consolidated data to save
            filename: Name of the file (without extension)

        Returns:
            Path to the saved file
        """
        consolidated_dir = self.output_dir / "consolidated"
        consolidated_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = consolidated_dir / f"{filename}_{timestamp}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved consolidated results to {filepath}")
        return filepath


def main():
    """
    Example usage of the API orchestrator.
    """
    # Initialize orchestrator
    orchestrator = APIOrchestrator()

    # Example 1: Search all APIs for a part
    print("\n=== Searching all APIs for part 0131M00008P ===")
    results = orchestrator.search_all_apis("0131M00008P")
    print(f"Found results from {len(results['results'])} APIs")

    # Example 2: Get detailed information
    print("\n=== Getting detailed information ===")
    details = orchestrator.get_part_details_from_all("0131M00008P")
    print(f"Retrieved details from {len(details['details'])} APIs")

    # Example 3: Search by model
    print("\n=== Searching by model number ===")
    model_results = orchestrator.search_by_model_all_apis("ARUF37C14")
    print(f"Found model info from {len(model_results['results'])} APIs")

    # Example 4: Get API info
    print("\n=== API Information ===")
    api_info = orchestrator.get_api_info()
    print(f"Total APIs configured: {api_info['total_apis']}")
    for api_name, info in api_info['apis'].items():
        print(f"\n{api_name}:")
        print(f"  Endpoints: {len(info['endpoints'])}")
        print(f"  Output: {info['output_dir']}")


if __name__ == "__main__":
    main()
