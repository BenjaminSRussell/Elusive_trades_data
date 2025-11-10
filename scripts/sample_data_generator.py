#!/usr/bin/env python3
"""
Generate sample training data for the Fugitive Data Pipeline.
Creates synthetic examples for NER and RE training.
"""

import json
import random
from pathlib import Path


# Sample parts database
MANUFACTURERS = ["Goodman", "Carrier", "Trane", "Honeywell", "White-Rodgers", "Supco", "Titan Pro", "Mars"]

PART_NUMBERS = [
    "0131M00008P", "0131M00008PS", "0131M00430SF",
    "ICM282A", "ICM283", "ICM284",
    "HC41AE235", "HC39GE208", "HC40GR233",
    "S9200U1000", "ST9120U", "S8610U",
    "TRCFD405", "SFCAP40D5440R", "POCFD505A",
]

EQUIPMENT_MODELS = [
    "ARUF37C14", "GMS9070", "GME95070BN20",
    "XL16i", "Infinity 20", "Comfort 15",
]

SPECS = [
    ("MFD", ["40+5", "35+5", "45+5", "50+5", "55+5", "60+5"]),
    ("Voltage", ["115V", "208-230V", "240V", "277V", "440V"]),
    ("HP", ["1/6", "1/4", "1/3", "1/2", "3/4", "1", "1.5"]),
    ("Temperature", ["-40 to 150°F", "0 to 200°F", "-20 to 180°F"]),
]

# Sentence templates
NER_TEMPLATES = [
    "The {manufacturer} {part_number} is a {spec} {component}.",
    "{part_number} is manufactured by {manufacturer} and rated for {spec}.",
    "This {manufacturer} {component} ({part_number}) has {spec} capacity.",
    "Model {equipment_model} uses the {manufacturer} {part_number}.",
    "The {part_number} is a {spec} replacement part for {equipment_model}.",
]

RE_TEMPLATES = {
    "REPLACES": [
        "The {part1} replaces the {part2}.",
        "{part1} is a replacement for {part2}.",
        "Use {part1} instead of {part2}.",
        "{part2} has been superseded by {part1}.",
    ],
    "EQUIVALENT_TO": [
        "{part1} is equivalent to {part2}.",
        "{part1} and {part2} are interchangeable.",
        "{part1} is the same as {part2}.",
    ],
    "COMPATIBLE_WITH": [
        "The {part} is compatible with {equipment}.",
        "{part} works with {equipment}.",
        "Use {part} for {equipment}.",
    ],
    "HAS_SPEC": [
        "The {part} is a {spec_value} {spec_type} {component}.",
        "{part} is rated for {spec_value}.",
        "This {part} has {spec_value} capacity.",
    ]
}


def generate_ner_example():
    """Generate a single NER training example."""
    template = random.choice(NER_TEMPLATES)

    manufacturer = random.choice(MANUFACTURERS)
    part_number = random.choice(PART_NUMBERS)
    equipment_model = random.choice(EQUIPMENT_MODELS)

    spec_type, spec_values = random.choice(SPECS)
    spec_value = random.choice(spec_values)
    spec = f"{spec_value} {spec_type}" if random.random() > 0.5 else spec_value

    components = ["motor", "capacitor", "control board", "igniter", "sensor", "valve"]
    component = random.choice(components)

    # Fill template
    text = template.format(
        manufacturer=manufacturer,
        part_number=part_number,
        equipment_model=equipment_model,
        spec=spec,
        component=component
    )

    # Find entity positions
    entities = []

    # Find manufacturer
    if manufacturer in text:
        start = text.find(manufacturer)
        entities.append([start, start + len(manufacturer), "MANUFACTURER"])

    # Find part number
    if part_number in text:
        start = text.find(part_number)
        entities.append([start, start + len(part_number), "PART_NUMBER"])

    # Find equipment model
    if equipment_model in text:
        start = text.find(equipment_model)
        entities.append([start, start + len(equipment_model), "EQUIPMENT_MODEL"])

    # Find spec
    if spec in text:
        start = text.find(spec)
        entities.append([start, start + len(spec), "SPECIFICATION"])

    return {"text": text, "entities": entities}


def generate_re_example():
    """Generate a single RE training example."""
    relation_type = random.choice(list(RE_TEMPLATES.keys()))
    template = random.choice(RE_TEMPLATES[relation_type])

    if relation_type == "REPLACES" or relation_type == "EQUIVALENT_TO":
        part1 = random.choice(PART_NUMBERS)
        part2 = random.choice([p for p in PART_NUMBERS if p != part1])

        text = template.format(part1=part1, part2=part2)

        entities = []
        start = text.find(part1)
        entities.append([start, start + len(part1), "PART_NUMBER"])

        start = text.find(part2)
        entities.append([start, start + len(part2), "PART_NUMBER"])

        relations = [{
            "source": part1,
            "target": part2,
            "relation": relation_type
        }]

    elif relation_type == "COMPATIBLE_WITH":
        part = random.choice(PART_NUMBERS)
        equipment = random.choice(EQUIPMENT_MODELS)

        text = template.format(part=part, equipment=equipment)

        entities = []
        start = text.find(part)
        entities.append([start, start + len(part), "PART_NUMBER"])

        start = text.find(equipment)
        entities.append([start, start + len(equipment), "EQUIPMENT_MODEL"])

        relations = [{
            "source": part,
            "target": equipment,
            "relation": relation_type
        }]

    else:  # HAS_SPEC
        part = random.choice(PART_NUMBERS)
        spec_type, spec_values = random.choice(SPECS)
        spec_value = random.choice(spec_values)
        component = random.choice(["motor", "capacitor", "control"])

        text = template.format(
            part=part,
            spec_type=spec_type,
            spec_value=spec_value,
            component=component
        )

        entities = []
        start = text.find(part)
        entities.append([start, start + len(part), "PART_NUMBER"])

        spec_full = spec_value
        if spec_full in text:
            start = text.find(spec_full)
            entities.append([start, start + len(spec_full), "SPECIFICATION"])

        relations = [{
            "source": part,
            "target": spec_value,
            "relation": "HAS_SPEC"
        }]

    return {
        "text": text,
        "entities": entities,
        "relations": relations
    }


def main():
    """Generate sample training data."""
    output_dir = Path("phase3_nlp/training_data")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate NER examples
    print("Generating NER training examples...")
    ner_examples = [generate_ner_example() for _ in range(100)]

    with open(output_dir / "sample_ner_training.json", "w") as f:
        json.dump(ner_examples, f, indent=2)

    print(f"✓ Created {len(ner_examples)} NER examples")

    # Generate RE examples
    print("Generating RE training examples...")
    re_examples = [generate_re_example() for _ in range(50)]

    with open(output_dir / "sample_re_training.json", "w") as f:
        json.dump(re_examples, f, indent=2)

    print(f"✓ Created {len(re_examples)} RE examples")

    # Show samples
    print("\nSample NER Example:")
    print(json.dumps(ner_examples[0], indent=2))

    print("\nSample RE Example:")
    print(json.dumps(re_examples[0], indent=2))

    print(f"\nFiles created in {output_dir}/")
    print("- sample_ner_training.json")
    print("- sample_re_training.json")


if __name__ == "__main__":
    main()
