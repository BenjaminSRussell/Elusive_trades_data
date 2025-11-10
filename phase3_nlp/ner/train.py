"""
Training pipeline for custom Named Entity Recognition.
Fine-tunes a transformer model on domain-specific entity types.
"""

import spacy
from spacy.tokens import DocBin
from spacy.training import Example
import random
import logging
from pathlib import Path
from typing import List, Tuple
import json

from phase3_nlp.ner.config import ENTITY_TYPES, BASE_MODEL, TRAINING_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NERTrainer:
    """
    Trains a custom NER model using spaCy transformers.
    """

    def __init__(self, base_model: str = BASE_MODEL):
        """
        Initialize NER trainer.

        Args:
            base_model: Name of base spaCy model to fine-tune
        """
        self.base_model = base_model
        self.nlp = None
        self.training_data = []

    def load_base_model(self):
        """Load the base transformer model."""
        try:
            logger.info(f"Loading base model: {self.base_model}")
            self.nlp = spacy.load(self.base_model)
            logger.info("Base model loaded successfully")
        except OSError:
            logger.info(f"Downloading {self.base_model}...")
            spacy.cli.download(self.base_model)
            self.nlp = spacy.load(self.base_model)

    def add_custom_entities(self):
        """Add custom entity types to the NER component."""
        if "ner" not in self.nlp.pipe_names:
            ner = self.nlp.add_pipe("ner")
        else:
            ner = self.nlp.get_pipe("ner")

        # Add custom entity labels
        for entity_type in ENTITY_TYPES:
            ner.add_label(entity_type)
            logger.info(f"Added entity label: {entity_type}")

    def load_training_data(self, training_file: str):
        """
        Load training data from JSON file.

        Expected format:
        [
            {
                "text": "The Goodman 0131M00008P is a 1/3 HP fan motor.",
                "entities": [[4, 11, "MANUFACTURER"], [12, 24, "PART_NUMBER"], ...]
            },
            ...
        ]

        Args:
            training_file: Path to JSON training data
        """
        logger.info(f"Loading training data from {training_file}")

        with open(training_file, 'r') as f:
            data = json.load(f)

        self.training_data = []
        for item in data:
            text = item['text']
            entities = item['entities']

            # Convert to spaCy format (start, end, label)
            spacy_entities = []
            for ent in entities:
                if len(ent) == 3:
                    start, end, label = ent
                    spacy_entities.append((start, end, label))

            self.training_data.append((text, {"entities": spacy_entities}))

        logger.info(f"Loaded {len(self.training_data)} training examples")

    def create_training_examples(self) -> List[Example]:
        """
        Convert training data to spaCy Example objects.

        Returns:
            List of spaCy Example objects
        """
        examples = []

        for text, annotations in self.training_data:
            doc = self.nlp.make_doc(text)
            example = Example.from_dict(doc, annotations)
            examples.append(example)

        return examples

    def train(self, output_dir: str, n_iter: int = None):
        """
        Train the NER model.

        Args:
            output_dir: Directory to save trained model
            n_iter: Number of training iterations (epochs)
        """
        if n_iter is None:
            n_iter = TRAINING_CONFIG['epochs']

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Prepare training examples
        examples = self.create_training_examples()

        # Get NER component
        ner = self.nlp.get_pipe("ner")

        # Disable other pipeline components during training
        other_pipes = [pipe for pipe in self.nlp.pipe_names if pipe != "ner"]
        with self.nlp.disable_pipes(*other_pipes):

            # Initialize optimizer
            optimizer = self.nlp.create_optimizer()

            # Training loop
            logger.info(f"Starting training for {n_iter} epochs...")

            for epoch in range(n_iter):
                random.shuffle(examples)
                losses = {}

                # Batch training
                batch_size = TRAINING_CONFIG['batch_size']
                for i in range(0, len(examples), batch_size):
                    batch = examples[i:i + batch_size]
                    self.nlp.update(
                        batch,
                        drop=TRAINING_CONFIG['dropout'],
                        losses=losses,
                        sgd=optimizer
                    )

                logger.info(f"Epoch {epoch + 1}/{n_iter} - Loss: {losses.get('ner', 0):.4f}")

        # Save the trained model
        logger.info(f"Saving model to {output_path}")
        self.nlp.to_disk(output_path)
        logger.info("Training complete!")

    def evaluate(self, test_data: List[Tuple[str, dict]]) -> dict:
        """
        Evaluate the trained model on test data.

        Args:
            test_data: List of (text, annotations) tuples

        Returns:
            Dictionary with evaluation metrics
        """
        examples = []
        for text, annotations in test_data:
            doc = self.nlp.make_doc(text)
            example = Example.from_dict(doc, annotations)
            examples.append(example)

        scores = self.nlp.evaluate(examples)

        logger.info("Evaluation Results:")
        logger.info(f"  Precision: {scores['ents_p']:.3f}")
        logger.info(f"  Recall: {scores['ents_r']:.3f}")
        logger.info(f"  F1-Score: {scores['ents_f']:.3f}")

        return scores


def create_sample_training_data(output_file: str):
    """
    Create a sample training data file for demonstration.

    Args:
        output_file: Path to save sample data
    """
    sample_data = [
        {
            "text": "The Goodman 0131M00008P is a 1/3 HP fan motor.",
            "entities": [[4, 11, "MANUFACTURER"], [12, 24, "PART_NUMBER"], [30, 36, "SPECIFICATION"]]
        },
        {
            "text": "The ICM282A replaces the 0131M00008P in the ARUF37C14 air handler.",
            "entities": [[4, 11, "PART_NUMBER"], [25, 37, "PART_NUMBER"], [45, 55, "EQUIPMENT_MODEL"]]
        },
        {
            "text": "This Honeywell S9200 will work if you also get the xyz adapter.",
            "entities": [[5, 14, "MANUFACTURER"], [15, 20, "EQUIPMENT_MODEL"], [52, 63, "ADAPTER"]]
        },
        {
            "text": "The Carrier HC41AE235 is a 40+5 MFD dual run capacitor rated for 370V.",
            "entities": [[4, 11, "MANUFACTURER"], [12, 21, "PART_NUMBER"], [27, 35, "SPECIFICATION"], [64, 68, "SPECIFICATION"]]
        },
        {
            "text": "Trane part number X13651019010 is compatible with the XE80 furnace.",
            "entities": [[0, 5, "MANUFACTURER"], [18, 31, "PART_NUMBER"], [55, 59, "EQUIPMENT_MODEL"]]
        },
    ]

    with open(output_file, 'w') as f:
        json.dump(sample_data, f, indent=2)

    logger.info(f"Created sample training data: {output_file}")


if __name__ == "__main__":
    # Example usage
    trainer = NERTrainer()

    # Create sample data if it doesn't exist
    sample_data_path = "phase3_nlp/training_data/sample_ner_training.json"
    Path(sample_data_path).parent.mkdir(parents=True, exist_ok=True)

    if not Path(sample_data_path).exists():
        create_sample_training_data(sample_data_path)

    # Load base model and add custom entities
    trainer.load_base_model()
    trainer.add_custom_entities()

    # Load training data
    trainer.load_training_data(sample_data_path)

    # Train model
    trainer.train(output_dir="phase3_nlp/models/custom_ner", n_iter=10)

    logger.info("NER training complete!")
