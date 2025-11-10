"""
Data Enricher for Phase 2.

This module combines matching and classification to enrich part data
with comprehensive information from all sources.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import logging
from datetime import datetime

from .matcher import PartMatcher
from .classifier import PartStatusClassifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PartEnricher:
    """
    Enriches part data by combining search results with AI classification.

    This is the main class for Phase 2, which:
    1. Searches for parts across all API data
    2. Classifies text for deprecation/replacement status
    3. Extracts relationships and cross-references
    4. Produces comprehensive enriched part data
    """

    def __init__(
        self,
        raw_data_dir: str = "data/raw",
        output_dir: str = "data/processed",
        model_name: str = "facebook/bart-large-mnli"
    ):
        """
        Initialize the enricher with matcher and classifier.

        Args:
            raw_data_dir: Directory containing Phase 1 API responses
            output_dir: Directory for storing enriched data
            model_name: HuggingFace model for zero-shot classification
        """
        self.matcher = PartMatcher(raw_data_dir, output_dir)
        self.classifier = PartStatusClassifier(model_name)
        self.output_dir = Path(output_dir)

        logger.info("Initialized PartEnricher")

    def enrich_part(self, part_number: str) -> Dict[str, Any]:
        """
        Perform complete enrichment for a part number.

        Args:
            part_number: The part number to enrich

        Returns:
            Dictionary containing comprehensive enriched data
        """
        logger.info(f"="*60)
        logger.info(f"Starting enrichment for part: {part_number}")
        logger.info(f"="*60)

        enriched = {
            "part_number": part_number,
            "timestamp": datetime.now().isoformat(),
            "search_results": {},
            "status": {},
            "relationships": {
                "cross_references": [],
                "replacements": [],
                "compatible_parts": []
            },
            "all_text_analyzed": [],
            "confidence_scores": {},
            "data_sources": []
        }

        # Step 1: Search for the part
        logger.info("Step 1: Searching for part across all APIs...")
        search_results = self.matcher.search_part(part_number)
        enriched["search_results"] = search_results
        enriched["data_sources"] = search_results["summary"]["apis_with_data"]

        # Step 2: Extract all text for classification
        logger.info("Step 2: Extracting text for classification...")
        all_text = self._extract_all_text(search_results)
        enriched["all_text_analyzed"] = all_text

        # Step 3: Classify status for each piece of text
        logger.info("Step 3: Running zero-shot classification...")
        status_results = self._classify_all_text(all_text)
        enriched["status"] = self._aggregate_status(status_results)

        # Step 4: Extract relationships
        logger.info("Step 4: Extracting relationships...")
        enriched["relationships"] = self._extract_all_relationships(search_results, status_results)

        # Step 5: Calculate confidence scores
        logger.info("Step 5: Calculating confidence scores...")
        enriched["confidence_scores"] = self._calculate_confidence_scores(search_results, status_results)

        # Step 6: Save enriched data
        logger.info("Step 6: Saving enriched data...")
        self._save_enriched_data(enriched, part_number)

        logger.info(f"Enrichment complete for {part_number}")
        return enriched

    def _extract_all_text(self, search_results: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Extract all text fields from search results for classification.

        Args:
            search_results: Results from PartMatcher

        Returns:
            List of dictionaries with text and source information
        """
        texts = []

        for match in search_results.get("matches", []):
            data = match.get("data", {})
            api = match.get("api", "unknown")

            # Extract description fields
            if "description" in data:
                texts.append({
                    "text": str(data["description"]),
                    "field": "description",
                    "api": api,
                    "source": "match_data"
                })

            # Extract status fields
            if "status" in data:
                texts.append({
                    "text": str(data["status"]),
                    "field": "status",
                    "api": api,
                    "source": "match_data"
                })

            # Extract nested data
            if "data" in data and isinstance(data["data"], dict):
                nested = data["data"]

                for key in ["description", "full_description", "notes", "lifecycle"]:
                    if key in nested:
                        texts.append({
                            "text": str(nested[key]),
                            "field": key,
                            "api": api,
                            "source": "nested_data"
                        })

        logger.info(f"Extracted {len(texts)} text fields for classification")
        return texts

    def _classify_all_text(self, texts: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Run classification on all extracted text.

        Args:
            texts: List of text dictionaries

        Returns:
            List of classification results
        """
        results = []

        for text_info in texts:
            text = text_info["text"]

            try:
                # Run all classifications
                classification = self.classifier.classify_all(text, threshold=0.5)

                results.append({
                    "text_info": text_info,
                    "classification": classification
                })

            except Exception as e:
                logger.error(f"Error classifying text: {e}")
                results.append({
                    "text_info": text_info,
                    "classification": None,
                    "error": str(e)
                })

        return results

    def _aggregate_status(self, status_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate classification results to determine overall status.

        Args:
            status_results: List of classification results

        Returns:
            Aggregated status information
        """
        deprecation_votes = []
        replacement_votes = []
        compatibility_votes = []

        for result in status_results:
            classification = result.get("classification")
            if not classification:
                continue

            # Collect deprecation indicators
            if classification["deprecation"]["is_deprecated"]:
                deprecation_votes.append(classification["deprecation"])

            # Collect replacement indicators
            if classification["replacement"]["has_replacement_info"]:
                replacement_votes.append(classification["replacement"])

            # Collect compatibility indicators
            if classification["compatibility"]["has_compatibility_info"]:
                compatibility_votes.append(classification["compatibility"])

        # Aggregate
        return {
            "is_deprecated": len(deprecation_votes) > 0,
            "deprecation_confidence": self._average_confidence(deprecation_votes),
            "deprecation_indicators": self._collect_unique_indicators(deprecation_votes),
            "has_replacement": len(replacement_votes) > 0,
            "replacement_confidence": self._average_confidence(replacement_votes),
            "replacement_indicators": self._collect_unique_indicators(replacement_votes),
            "has_compatibility_info": len(compatibility_votes) > 0,
            "compatibility_confidence": self._average_confidence(compatibility_votes),
            "compatibility_indicators": self._collect_unique_indicators(compatibility_votes)
        }

    def _average_confidence(self, votes: List[Dict[str, Any]]) -> float:
        """Calculate average confidence from votes."""
        if not votes:
            return 0.0

        total = 0.0
        count = 0

        for vote in votes:
            indicators = vote.get("deprecation_indicators") or vote.get("replacement_indicators") or vote.get("compatibility_indicators", [])
            for indicator in indicators:
                total += indicator["confidence"]
                count += 1

        return total / count if count > 0 else 0.0

    def _collect_unique_indicators(self, votes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Collect unique indicators from votes."""
        seen = set()
        unique = []

        for vote in votes:
            indicators = vote.get("deprecation_indicators") or vote.get("replacement_indicators") or vote.get("compatibility_indicators", [])
            for indicator in indicators:
                label = indicator["label"]
                if label not in seen:
                    seen.add(label)
                    unique.append(indicator)

        return unique

    def _extract_all_relationships(
        self,
        search_results: Dict[str, Any],
        status_results: List[Dict[str, Any]]
    ) -> Dict[str, List]:
        """
        Extract all relationships from search and classification results.

        Args:
            search_results: Results from search
            status_results: Classification results

        Returns:
            Dictionary of relationships
        """
        relationships = {
            "cross_references": [],
            "replacements": [],
            "compatible_parts": []
        }

        # From search results
        relationships["cross_references"] = search_results.get("cross_references", [])
        relationships["replacements"] = search_results.get("replacements", [])

        # Extract part numbers from classified text
        for result in status_results:
            text_info = result.get("text_info", {})
            classification = result.get("classification")

            if not classification:
                continue

            text = text_info.get("text", "")

            # If text indicates replacement, extract part numbers
            if classification["replacement"]["has_replacement_info"]:
                part_numbers = self.classifier.extract_part_numbers_from_text(text)
                for pn in part_numbers:
                    relationships["replacements"].append({
                        "part_number": pn,
                        "source": "classification",
                        "confidence": classification["replacement"]["replacement_confidence"] if "replacement_confidence" in classification["replacement"] else 0.5
                    })

            # If text indicates compatibility, extract part numbers
            if classification["compatibility"]["has_compatibility_info"]:
                part_numbers = self.classifier.extract_part_numbers_from_text(text)
                for pn in part_numbers:
                    relationships["compatible_parts"].append({
                        "part_number": pn,
                        "source": "classification",
                        "confidence": classification["compatibility"]["compatibility_confidence"] if "compatibility_confidence" in classification["compatibility"] else 0.5
                    })

        # Remove duplicates
        relationships["cross_references"] = self._deduplicate_parts(relationships["cross_references"])
        relationships["replacements"] = self._deduplicate_parts(relationships["replacements"])
        relationships["compatible_parts"] = self._deduplicate_parts(relationships["compatible_parts"])

        return relationships

    def _deduplicate_parts(self, parts: List[Any]) -> List[Any]:
        """Remove duplicate parts from list."""
        seen = set()
        unique = []

        for part in parts:
            if isinstance(part, dict):
                identifier = part.get("part_number", str(part))
            else:
                identifier = str(part)

            if identifier not in seen:
                seen.add(identifier)
                unique.append(part)

        return unique

    def _calculate_confidence_scores(
        self,
        search_results: Dict[str, Any],
        status_results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate overall confidence scores.

        Args:
            search_results: Search results
            status_results: Classification results

        Returns:
            Dictionary of confidence scores
        """
        return {
            "data_availability": min(1.0, len(search_results.get("matches", [])) / 4.0),  # Normalize to max 4 APIs
            "classification_confidence": self._average_all_confidences(status_results),
            "relationship_confidence": min(1.0, (
                len(search_results.get("cross_references", [])) +
                len(search_results.get("replacements", []))
            ) / 5.0)  # Normalize
        }

    def _average_all_confidences(self, status_results: List[Dict[str, Any]]) -> float:
        """Calculate average of all classification confidences."""
        confidences = []

        for result in status_results:
            classification = result.get("classification")
            if not classification:
                continue

            for key in ["deprecation", "replacement", "compatibility"]:
                indicators = classification[key].get(f"{key}_indicators", [])
                for indicator in indicators:
                    confidences.append(indicator["confidence"])

        return sum(confidences) / len(confidences) if confidences else 0.0

    def _save_enriched_data(self, enriched: Dict[str, Any], part_number: str):
        """
        Save enriched data to file.

        Args:
            enriched: Enriched data dictionary
            part_number: Part number
        """
        # Normalize part number for directory name
        normalized = self.matcher._normalize_part_number(part_number)
        part_dir = self.output_dir / normalized
        part_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = part_dir / f"enriched_{timestamp}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(enriched, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved enriched data to {filepath}")


def main():
    """
    Example usage of the PartEnricher.
    """
    print("\n" + "="*60)
    print("Part Enrichment Example")
    print("="*60)

    enricher = PartEnricher()

    # Enrich a part
    part_number = "0131M00008P"
    print(f"\nEnriching part: {part_number}")

    enriched = enricher.enrich_part(part_number)

    print(f"\n--- Enrichment Summary ---")
    print(f"Part Number: {enriched['part_number']}")
    print(f"Data Sources: {enriched['data_sources']}")
    print(f"Is Deprecated: {enriched['status']['is_deprecated']}")
    print(f"Has Replacement: {enriched['status']['has_replacement']}")
    print(f"Cross References: {len(enriched['relationships']['cross_references'])}")
    print(f"Replacements: {len(enriched['relationships']['replacements'])}")
    print(f"Compatible Parts: {len(enriched['relationships']['compatible_parts'])}")
    print(f"\nConfidence Scores:")
    for key, value in enriched['confidence_scores'].items():
        print(f"  {key}: {value:.2f}")


if __name__ == "__main__":
    main()
