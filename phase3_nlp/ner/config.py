"""
Configuration for custom Named Entity Recognition.
Defines domain-specific entity types and training parameters.
"""

# Custom entity types for HVAC/plumbing domain
ENTITY_TYPES = [
    "PART_NUMBER",      # e.g., "0131M00008P", "ICM282A"
    "MANUFACTURER",     # e.g., "Goodman", "Carrier", "Honeywell"
    "SPECIFICATION",    # e.g., "40+5 MFD", "1/2 HP", "208-230V"
    "EQUIPMENT_MODEL",  # e.g., "S9200", "ARUF37C14"
    "ADAPTER",          # e.g., "xyz adapter", "mounting bracket"
]

# spaCy transformer model configuration
BASE_MODEL = "en_core_web_trf"  # BERT-compatible transformer model

# Training configuration
TRAINING_CONFIG = {
    "batch_size": 32,
    "learn_rate": 2e-5,
    "epochs": 20,
    "dropout": 0.1,
    "patience": 3,  # Early stopping patience
}

# Annotation guidelines for training data
ANNOTATION_GUIDELINES = """
# Entity Annotation Guidelines

## PART_NUMBER
- Alphanumeric identifiers for specific parts
- Usually contain numbers and letters (sometimes dashes/underscores)
- Examples: "0131M00008P", "ICM282A", "HC41AE235"

## MANUFACTURER
- Company names that make HVAC/plumbing equipment
- Examples: "Goodman", "Carrier", "Trane", "Honeywell", "White-Rodgers"

## SPECIFICATION
- Technical specifications with units
- Patterns: [number] [unit]
- Examples:
  - Capacitance: "40+5 MFD", "45 µF"
  - Horsepower: "1/2 HP", "1/4 HP"
  - Voltage: "208-230V", "115V"
  - Temperature: "55°F", "-40 to 150°F"

## EQUIPMENT_MODEL
- Model numbers for complete units (furnaces, air handlers, etc.)
- Usually longer than part numbers
- Examples: "ARUF37C14", "GME95070BN20", "S9200U1000"

## ADAPTER
- Parts that enable compatibility between other parts
- Often contain keywords: "adapter", "bracket", "kit"
- Examples: "mounting bracket", "xyz adapter", "conversion kit"
"""

# Example annotated sentences for reference
EXAMPLE_ANNOTATIONS = [
    {
        "text": "The Goodman 0131M00008P is a 1/3 HP fan motor.",
        "entities": [
            (4, 11, "MANUFACTURER"),    # "Goodman"
            (12, 24, "PART_NUMBER"),    # "0131M00008P"
            (30, 36, "SPECIFICATION"),  # "1/3 HP"
        ]
    },
    {
        "text": "The ICM282A replaces the 0131M00008P in the ARUF37C14 air handler.",
        "entities": [
            (4, 11, "PART_NUMBER"),     # "ICM282A"
            (25, 37, "PART_NUMBER"),    # "0131M00008P"
            (45, 55, "EQUIPMENT_MODEL"), # "ARUF37C14"
        ]
    },
    {
        "text": "This Honeywell S9200 will work if you also get the xyz adapter.",
        "entities": [
            (5, 14, "MANUFACTURER"),    # "Honeywell"
            (15, 20, "EQUIPMENT_MODEL"), # "S9200"
            (52, 63, "ADAPTER"),        # "xyz adapter"
        ]
    },
]
