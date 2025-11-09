"""
Custom Relation Extraction component for spaCy.
Extracts relationships between entities (REPLACES, EQUIVALENT_TO, etc.)
Following the official spaCy 3 tutorial for custom RE components.
"""

import spacy
from spacy.tokens import Doc, Span
from spacy.language import Language
from spacy.training import Example
import numpy as np
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


# Relation types to extract
RELATION_TYPES = [
    "REPLACES",         # Part A replaces Part B
    "EQUIVALENT_TO",    # Part A is equivalent to Part B
    "COMPATIBLE_WITH",  # Part A is compatible with Equipment B
    "ADAPTER_REQUIRED", # Part A requires Adapter B
    "HAS_SPEC",        # Part A has Specification B
]


# Register custom extension for storing relations
if not Doc.has_extension("relations"):
    Doc.set_extension("relations", default=[])


@Language.factory("relation_extractor")
class RelationExtractor:
    """
    Custom spaCy component for extracting relationships between entities.
    """

    def __init__(self, nlp: Language, name: str = "relation_extractor"):
        """
        Initialize the relation extractor.

        Args:
            nlp: spaCy Language object
            name: Component name
        """
        self.nlp = nlp
        self.name = name
        self.relation_types = RELATION_TYPES

        # Patterns that indicate specific relationships
        self.relation_patterns = {
            "REPLACES": [
                "replaces", "replacement for", "supersedes", "instead of",
                "use instead", "substitute for", "updated from"
            ],
            "EQUIVALENT_TO": [
                "equivalent to", "same as", "equals", "identical to",
                "also known as", "interchangeable with", "cross-reference"
            ],
            "COMPATIBLE_WITH": [
                "compatible with", "works with", "fits", "designed for",
                "for use with", "used in", "installed in"
            ],
            "ADAPTER_REQUIRED": [
                "requires adapter", "needs adapter", "requires mounting",
                "with adapter", "adapter required", "also get", "also need"
            ],
            "HAS_SPEC": [
                "is a", "rated for", "rated at", "capacity of",
                "voltage of", "horsepower"
            ],
        }

    def __call__(self, doc: Doc) -> Doc:
        """
        Process a document to extract relations.

        Args:
            doc: spaCy Doc object with entities

        Returns:
            Doc object with relations stored in doc._.relations
        """
        relations = []

        # Get all entities
        entities = list(doc.ents)

        # Check all pairs of entities
        for i, ent1 in enumerate(entities):
            for ent2 in entities[i + 1:]:
                # Get text between entities
                start = min(ent1.end, ent2.end)
                end = max(ent1.start, ent2.start)

                context = doc[start:end].text.lower()

                # Check for relation patterns
                relation_type = self._classify_relation(ent1, ent2, context)

                if relation_type:
                    relations.append({
                        "source": ent1.text,
                        "source_label": ent1.label_,
                        "target": ent2.text,
                        "target_label": ent2.label_,
                        "relation": relation_type,
                        "context": context,
                        "confidence": 0.85  # Placeholder - would come from ML model
                    })

        doc._.relations = relations
        return doc

    def _classify_relation(self, ent1: Span, ent2: Span, context: str) -> str:
        """
        Classify the relationship between two entities based on context.

        Args:
            ent1: First entity
            ent2: Second entity
            context: Text between entities

        Returns:
            Relation type or None
        """
        # Check for explicit relation patterns
        for relation_type, patterns in self.relation_patterns.items():
            if any(pattern in context for pattern in patterns):
                # Validate entity type compatibility
                if self._is_valid_relation(ent1.label_, ent2.label_, relation_type):
                    return relation_type

        return None

    def _is_valid_relation(self, label1: str, label2: str, relation: str) -> bool:
        """
        Check if a relation is valid for the given entity types.

        Args:
            label1: First entity label
            label2: Second entity label
            relation: Relation type

        Returns:
            True if valid, False otherwise
        """
        valid_combinations = {
            "REPLACES": [
                ("PART_NUMBER", "PART_NUMBER"),
            ],
            "EQUIVALENT_TO": [
                ("PART_NUMBER", "PART_NUMBER"),
            ],
            "COMPATIBLE_WITH": [
                ("PART_NUMBER", "EQUIPMENT_MODEL"),
                ("EQUIPMENT_MODEL", "PART_NUMBER"),
            ],
            "ADAPTER_REQUIRED": [
                ("PART_NUMBER", "ADAPTER"),
                ("EQUIPMENT_MODEL", "ADAPTER"),
            ],
            "HAS_SPEC": [
                ("PART_NUMBER", "SPECIFICATION"),
                ("EQUIPMENT_MODEL", "SPECIFICATION"),
            ],
        }

        allowed = valid_combinations.get(relation, [])
        return (label1, label2) in allowed or (label2, label1) in allowed


class RelationTrainer:
    """
    Trains the relation extraction component.
    """

    def __init__(self, nlp):
        """
        Initialize relation trainer.

        Args:
            nlp: spaCy pipeline with NER component
        """
        self.nlp = nlp

    def create_training_examples(self, annotated_data: List[Dict]) -> List[Example]:
        """
        Create training examples from annotated data.

        Expected format:
        [
            {
                "text": "The ICM282A replaces the 0131M00008P.",
                "entities": [...],
                "relations": [
                    {
                        "source": "ICM282A",
                        "target": "0131M00008P",
                        "relation": "REPLACES"
                    }
                ]
            },
            ...
        ]

        Args:
            annotated_data: List of annotated documents

        Returns:
            List of spaCy Example objects
        """
        examples = []

        for item in annotated_data:
            doc = self.nlp.make_doc(item['text'])

            # Create gold standard annotations
            gold_annotations = {
                "entities": item['entities'],
                "relations": item.get('relations', [])
            }

            example = Example.from_dict(doc, gold_annotations)
            examples.append(example)

        return examples


def create_sample_relation_training_data(output_file: str):
    """
    Create sample training data for relation extraction.

    Args:
        output_file: Path to save sample data
    """
    import json

    sample_data = [
        {
            "text": "The ICM282A replaces the 0131M00008P.",
            "entities": [[4, 11, "PART_NUMBER"], [25, 37, "PART_NUMBER"]],
            "relations": [
                {"source": "ICM282A", "target": "0131M00008P", "relation": "REPLACES"}
            ]
        },
        {
            "text": "The Honeywell S9200 is compatible with the ARUF37C14 if you also get the xyz adapter.",
            "entities": [
                [4, 13, "MANUFACTURER"],
                [14, 19, "EQUIPMENT_MODEL"],
                [43, 53, "EQUIPMENT_MODEL"],
                [73, 84, "ADAPTER"]
            ],
            "relations": [
                {"source": "S9200", "target": "ARUF37C14", "relation": "COMPATIBLE_WITH"},
                {"source": "S9200", "target": "xyz adapter", "relation": "ADAPTER_REQUIRED"}
            ]
        },
        {
            "text": "The Carrier HC41AE235 is a 40+5 MFD dual run capacitor.",
            "entities": [
                [4, 11, "MANUFACTURER"],
                [12, 21, "PART_NUMBER"],
                [27, 35, "SPECIFICATION"]
            ],
            "relations": [
                {"source": "HC41AE235", "target": "40+5 MFD", "relation": "HAS_SPEC"}
            ]
        },
    ]

    from pathlib import Path
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(sample_data, f, indent=2)

    logger.info(f"Created sample relation training data: {output_file}")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Load NER model
    nlp = spacy.load("en_core_web_sm")

    # Add relation extractor to pipeline
    nlp.add_pipe("relation_extractor")

    # Test with sample text
    text = "The ICM282A replaces the 0131M00008P in most Goodman furnaces."

    doc = nlp(text)

    print(f"Relations found: {len(doc._.relations)}")
    for rel in doc._.relations:
        print(f"  {rel['source']} --[{rel['relation']}]--> {rel['target']}")
