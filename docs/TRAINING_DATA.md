# Training Data Annotation Guide

This guide shows you how to create high-quality training data for custom NER and Relation Extraction models.

---

## Overview

The pipeline uses **spaCy transformers** fine-tuned on domain-specific data. To train accurate models, you need:

1. **NER Training Data**: 500-1000+ annotated sentences with entity labels
2. **RE Training Data**: 300-500+ sentences with relationship annotations

---

## Method 1: Using Prodigy (Recommended)

[Prodigy](https://prodi.gy) is spaCy's commercial annotation tool ($390/developer).

### Setup

```bash
# Install Prodigy
pip install prodigy -f https://XXXX-XXXX-XXXX-XXXX@download.prodi.gy

# Or use trial license
```

### Annotate Entities

```bash
# Create NER annotation task
prodigy ner.manual hvac_ner en_core_web_sm ./sample_texts.jsonl \
    --label PART_NUMBER,MANUFACTURER,SPECIFICATION,EQUIPMENT_MODEL,ADAPTER

# Annotate in browser (http://localhost:8080)
# - Highlight "0131M00008P" → Label as PART_NUMBER
# - Highlight "Goodman" → Label as MANUFACTURER
# - Highlight "1/3 HP" → Label as SPECIFICATION
```

### Annotate Relationships

```bash
# Create relation annotation task
prodigy rel.manual hvac_relations en_core_web_sm ./ner_output.jsonl \
    --label REPLACES,EQUIVALENT_TO,COMPATIBLE_WITH,ADAPTER_REQUIRED,HAS_SPEC

# Mark relationships between entities:
# - ICM282A [REPLACES] 0131M00008P
# - Goodman [MANUFACTURED] 0131M00008P
```

### Export Training Data

```bash
# Export to spaCy format
prodigy db-out hvac_ner > phase3_nlp/training_data/ner_annotations.jsonl
prodigy db-out hvac_relations > phase3_nlp/training_data/re_annotations.jsonl
```

---

## Method 2: Using Label Studio (Free & Open Source)

[Label Studio](https://labelstud.io) is a free alternative.

### Setup

```bash
# Install
pip install label-studio

# Start server
label-studio start

# Open http://localhost:8080
```

### Create NER Project

1. **Create Project** → "HVAC Parts NER"
2. **Labeling Setup** → Use this config:

```xml
<View>
  <Labels name="label" toName="text">
    <Label value="PART_NUMBER" background="red"/>
    <Label value="MANUFACTURER" background="blue"/>
    <Label value="SPECIFICATION" background="green"/>
    <Label value="EQUIPMENT_MODEL" background="purple"/>
    <Label value="ADAPTER" background="orange"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
```

3. **Import Data** → Upload `sample_texts.txt`
4. **Start Annotating**

### Export

1. **Export** → JSON
2. Convert to spaCy format:

```python
python scripts/convert_labelstudio_to_spacy.py \
    labelstudio_export.json \
    phase3_nlp/training_data/ner_annotations.jsonl
```

---

## Method 3: Manual Annotation (Free but Tedious)

### Create Training JSON

Edit `phase3_nlp/training_data/ner_training.json`:

```json
[
  {
    "text": "The Goodman 0131M00008P is a 1/3 HP condenser fan motor.",
    "entities": [
      [4, 11, "MANUFACTURER"],
      [12, 24, "PART_NUMBER"],
      [30, 36, "SPECIFICATION"]
    ]
  },
  {
    "text": "The ICM282A replaces the 0131M00008P in the ARUF37C14 air handler.",
    "entities": [
      [4, 11, "PART_NUMBER"],
      [25, 37, "PART_NUMBER"],
      [45, 55, "EQUIPMENT_MODEL"]
    ]
  }
]
```

**Entity Format**: `[start_char, end_char, "LABEL"]`

---

## Getting Sample Texts for Annotation

### From PostgreSQL Evidence Store

```bash
# Export random document excerpts
make shell-postgres

# Then:
COPY (
  SELECT raw_text_content
  FROM documents
  WHERE document_type = 'pdf'
    AND LENGTH(raw_text_content) BETWEEN 100 AND 500
  ORDER BY RANDOM()
  LIMIT 1000
) TO '/tmp/sample_texts.txt';
```

### From Web Scraping

```bash
# Scrape and extract text
make scrape-test

# Then export from database
```

---

## Annotation Guidelines

### PART_NUMBER
- **Format**: Alphanumeric with optional dashes/underscores
- **Examples**: `0131M00008P`, `ICM282A`, `HC41AE235`
- **NOT**: Serial numbers, order numbers

### MANUFACTURER
- **Format**: Company names
- **Examples**: `Goodman`, `Carrier`, `Trane`, `Honeywell`
- **Include**: Brand names even if parent company differs

### SPECIFICATION
- **Format**: Number + unit
- **Examples**:
  - `1/3 HP` (horsepower)
  - `40+5 MFD` (capacitance)
  - `208-230V` (voltage)
  - `1/2" x 3"` (dimensions)
- **Include**: Units even if abbreviated

### EQUIPMENT_MODEL
- **Format**: Model numbers for complete units
- **Examples**: `ARUF37C14`, `GMS9070`, `S9200U1000`
- **Distinction**: Longer/more complex than part numbers

### ADAPTER
- **Format**: Parts that enable compatibility
- **Examples**: `mounting bracket`, `xyz adapter`, `conversion kit`
- **Keywords**: adapter, bracket, kit, mounting

---

## Relation Annotation Guidelines

### REPLACES
- **Pattern**: "Part A replaces Part B"
- **Example**: "The ICM282A replaces the 0131M00008P"
- **Direction**: New part → Old part

### EQUIVALENT_TO
- **Pattern**: "Part A is equivalent to Part B"
- **Example**: "Janitrol ABC123 is equivalent to Goodman XYZ789"
- **Bidirectional**: Can go either direction

### COMPATIBLE_WITH
- **Pattern**: "Part works with Equipment"
- **Example**: "The S9200 is compatible with the ARUF37C14"

### ADAPTER_REQUIRED
- **Pattern**: "Part needs Adapter"
- **Example**: "The S9200 requires the xyz adapter"
- **Context**: Often from forum posts

### HAS_SPEC
- **Pattern**: "Part has Specification"
- **Example**: "The HC41AE235 is a 40+5 MFD capacitor"

---

## Quality Metrics

### Good Training Data Has:

✓ **Consistency**: Same entities labeled the same way
✓ **Coverage**: Diverse examples from different sources
✓ **Balance**: Similar quantities of each label type
✓ **Context**: Enough surrounding text to understand
✓ **Accuracy**: Double-checked annotations

### Minimum Quantities:

| Data Type | Minimum | Recommended |
|-----------|---------|-------------|
| NER Examples | 500 | 1000+ |
| RE Examples | 300 | 500+ |
| Unique Parts | 100 | 300+ |
| Manufacturers | 10 | 20+ |

---

## Using Your Annotations

### 1. Save to Training Data Directory

```bash
# NER data
cp annotations.jsonl phase3_nlp/training_data/ner_training.jsonl

# RE data
cp relations.jsonl phase3_nlp/training_data/re_training.jsonl
```

### 2. Train the Model

```bash
# Train NER
make train-ner

# Train RE (after NER is trained)
python phase3_nlp/relation_extraction/train.py
```

### 3. Test the Model

```python
import spacy

# Load your trained model
nlp = spacy.load("phase3_nlp/models/custom_ner")

# Test
text = "The Goodman 0131M00008P is a 1/3 HP motor."
doc = nlp(text)

for ent in doc.ents:
    print(f"{ent.text} → {ent.label_}")
```

---

## Active Learning Workflow (Advanced)

Use your pipeline to help annotation:

1. **Run pipeline on new documents**
2. **Extract low-confidence predictions**
3. **Manually correct them**
4. **Add to training data**
5. **Retrain model**
6. **Repeat**

```python
# Extract low-confidence entities for review
from phase3_nlp.processors.nlp_processor import NLPProcessor

processor = NLPProcessor()
doc = processor.nlp("Your text here")

for ent in doc.ents:
    if ent._.confidence < 0.7:  # Low confidence
        print(f"Review: {ent.text} ({ent.label_}) - {ent._.confidence:.2f}")
```

---

## Tips for Fast Annotation

1. **Batch Similar Texts**: Annotate all motor specs together, then all capacitors
2. **Use Keyboard Shortcuts**: Learn Prodigy/Label Studio hotkeys
3. **Start Simple**: Begin with obvious entities, add edge cases later
4. **Take Breaks**: Annotation fatigue leads to errors
5. **Double-Check**: Review 10% of annotations for quality

---

## Example Annotation Session (1 hour)

1. **0-10 min**: Setup Prodigy/Label Studio
2. **10-50 min**: Annotate 100 sentences (~2.5 per minute)
3. **50-60 min**: Review and export

**Repeat daily for 1-2 weeks to get 500-1000 examples.**

---

## Next Steps

After annotation:
1. Train models: See `docs/MODEL_TRAINING.md`
2. Evaluate accuracy
3. Deploy updated models
4. Monitor performance in production

---

## Resources

- [Prodigy Documentation](https://prodi.gy/docs/)
- [Label Studio Guide](https://labelstud.io/guide/)
- [spaCy Training](https://spacy.io/usage/training)
- [Active Learning](https://prodi.gy/docs/active-learning)
