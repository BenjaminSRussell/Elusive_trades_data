"""
Part Number Matcher for Phase 2.

This module searches through Phase 1 API data to find and match part numbers.
"""

from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
import logging
from datetime import datetime
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PartMatcher:
    """
    Searches and matches parts across multiple API data sources.

    This class reads data from Phase 1 outputs and performs intelligent
    matching to find parts, cross-references, and replacements.
    """

    def __init__(self, raw_data_dir: str = "data/raw", output_dir: str = "data/processed"):
        """
        Initialize the part matcher.

        Args:
            raw_data_dir: Directory containing Phase 1 API responses
            output_dir: Directory for storing processed match results
        """
        self.raw_data_dir = Path(raw_data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized PartMatcher")
        logger.info(f"Raw data directory: {self.raw_data_dir}")
        logger.info(f"Output directory: {self.output_dir}")

    def search_part(self, part_number: str) -> Dict[str, Any]:
        """
        Search for a part across all available API data.

        Args:
            part_number: The part number to search for

        Returns:
            Dictionary containing all matching data found
        """
        logger.info(f"Searching for part number: {part_number}")

        results = {
            "part_number": part_number,
            "timestamp": datetime.now().isoformat(),
            "matches": [],
            "cross_references": [],
            "replacements": [],
            "summary": {
                "total_matches": 0,
                "apis_with_data": [],
                "has_replacement": False,
                "is_deprecated": False
            }
        }

        # Search through all API data directories
        if not self.raw_data_dir.exists():
            logger.warning(f"Raw data directory does not exist: {self.raw_data_dir}")
            return results

        for api_dir in self.raw_data_dir.iterdir():
            if not api_dir.is_dir():
                continue

            api_name = api_dir.name
            logger.info(f"Searching {api_name} data...")

            matches = self._search_in_api_data(api_dir, part_number)
            if matches:
                results["matches"].extend(matches)
                results["summary"]["apis_with_data"].append(api_name)

        results["summary"]["total_matches"] = len(results["matches"])

        # Extract cross-references and replacements
        self._extract_relationships(results)

        # Save results
        self._save_match_results(results, part_number)

        return results

    def _search_in_api_data(self, api_dir: Path, part_number: str) -> List[Dict[str, Any]]:
        """
        Search for a part in a specific API's data directory.

        Args:
            api_dir: Path to the API data directory
            part_number: Part number to search for

        Returns:
            List of matching records
        """
        matches = []

        # Iterate through all session directories
        for session_dir in api_dir.iterdir():
            if not session_dir.is_dir():
                continue

            # Search all JSON files in this session
            for json_file in session_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Check if this file contains the part number
                    if self._contains_part_number(data, part_number):
                        matches.append({
                            "api": api_dir.name,
                            "session": session_dir.name,
                            "file": json_file.name,
                            "data": data
                        })
                        logger.info(f"Found match in {api_dir.name}/{json_file.name}")

                except json.JSONDecodeError as e:
                    logger.error(f"Error reading {json_file}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error reading {json_file}: {e}")

        return matches

    def _contains_part_number(self, data: Any, part_number: str) -> bool:
        """
        Recursively check if data contains the part number.

        Args:
            data: Data structure to search
            part_number: Part number to find

        Returns:
            True if part number is found, False otherwise
        """
        # Normalize part numbers for comparison (remove spaces, dashes, case-insensitive)
        normalized_search = self._normalize_part_number(part_number)

        if isinstance(data, dict):
            for key, value in data.items():
                # Check if key or value contains the part number
                if isinstance(value, str):
                    if self._normalize_part_number(value) == normalized_search:
                        return True
                elif self._contains_part_number(value, part_number):
                    return True

        elif isinstance(data, list):
            for item in data:
                if self._contains_part_number(item, part_number):
                    return True

        elif isinstance(data, str):
            if self._normalize_part_number(data) == normalized_search:
                return True

        return False

    def _normalize_part_number(self, part_number: str) -> str:
        """
        Normalize a part number for comparison.

        Args:
            part_number: Part number to normalize

        Returns:
            Normalized part number
        """
        # Remove spaces, dashes, and convert to uppercase
        return re.sub(r'[\s\-]', '', part_number).upper()

    def _extract_relationships(self, results: Dict[str, Any]):
        """
        Extract cross-references and replacement relationships from matches.

        Args:
            results: Results dictionary to populate
        """
        for match in results["matches"]:
            data = match.get("data", {})

            # Look for cross-references
            if "cross_references" in data:
                refs = data["cross_references"]
                if isinstance(refs, list):
                    results["cross_references"].extend(refs)

            # Look for replacements
            if "replaces" in data or "replacements" in data:
                replacements = data.get("replaces", data.get("replacements", []))
                if replacements:
                    results["replacements"].extend(replacements)
                    results["summary"]["has_replacement"] = True

            # Check for replacement info
            if "replaced_by" in data or "superseded_by" in data:
                replacement = data.get("replaced_by") or data.get("superseded_by")
                if replacement:
                    results["replacements"].append({
                        "type": "replaced_by",
                        "part_number": replacement
                    })
                    results["summary"]["has_replacement"] = True

    def find_cross_references(self, part_number: str) -> Dict[str, Any]:
        """
        Find all cross-reference parts for a given part number.

        Args:
            part_number: The part number to find cross-references for

        Returns:
            Dictionary containing cross-reference information
        """
        logger.info(f"Finding cross-references for: {part_number}")

        # First search for the part
        search_results = self.search_part(part_number)

        cross_refs = {
            "source_part": part_number,
            "timestamp": datetime.now().isoformat(),
            "cross_references": search_results["cross_references"],
            "total_found": len(search_results["cross_references"])
        }

        return cross_refs

    def find_replacements(self, part_number: str) -> Dict[str, Any]:
        """
        Find replacement parts for a given part number.

        Args:
            part_number: The part number to find replacements for

        Returns:
            Dictionary containing replacement information
        """
        logger.info(f"Finding replacements for: {part_number}")

        # Search for the part
        search_results = self.search_part(part_number)

        replacements = {
            "original_part": part_number,
            "timestamp": datetime.now().isoformat(),
            "replacements": search_results["replacements"],
            "has_replacement": search_results["summary"]["has_replacement"],
            "total_found": len(search_results["replacements"])
        }

        return replacements

    def _save_match_results(self, results: Dict[str, Any], part_number: str):
        """
        Save match results to the processed data directory.

        Args:
            results: Match results to save
            part_number: Part number (used in filename)
        """
        # Create directory for this part
        part_dir = self.output_dir / self._normalize_part_number(part_number)
        part_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = part_dir / f"match_results_{timestamp}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved match results to {filepath}")

    def get_part_history(self, part_number: str) -> List[Dict[str, Any]]:
        """
        Get all previous search results for a part number.

        Args:
            part_number: The part number

        Returns:
            List of all previous search results
        """
        part_dir = self.output_dir / self._normalize_part_number(part_number)

        if not part_dir.exists():
            logger.info(f"No history found for {part_number}")
            return []

        history = []
        for json_file in sorted(part_dir.glob("match_results_*.json")):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    history.append(data)
            except Exception as e:
                logger.error(f"Error reading history file {json_file}: {e}")

        return history


def main():
    """
    Example usage of the PartMatcher.
    """
    matcher = PartMatcher()

    # Example: Search for a part
    print("\n=== Searching for part 0131M00008P ===")
    results = matcher.search_part("0131M00008P")
    print(f"Total matches found: {results['summary']['total_matches']}")
    print(f"APIs with data: {results['summary']['apis_with_data']}")
    print(f"Has replacement: {results['summary']['has_replacement']}")

    # Example: Find cross-references
    print("\n=== Finding cross-references ===")
    cross_refs = matcher.find_cross_references("0131M00008P")
    print(f"Total cross-references: {cross_refs['total_found']}")

    # Example: Find replacements
    print("\n=== Finding replacements ===")
    replacements = matcher.find_replacements("0131M00008P")
    print(f"Has replacement: {replacements['has_replacement']}")


if __name__ == "__main__":
    main()
