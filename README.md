# HVAC Parts Search System

A deterministic, file-based system for searching and enriching HVAC parts data across multiple supplier APIs.

## Architecture Overview

This system consists of **two phases**:

1. **Phase 1**: Multi-API data acquisition from HVAC suppliers
2. **Phase 2**: Part number matching and data enrichment with zero-shot classification

All data is stored locally in the `data/` directory - **no databases, no Docker, no passwords**.

---

## Directory Structure

```
Elusive_trades_data/
├── phase1_acquisition/          # API data acquisition
│   ├── apis/                    # API adapters
│   │   ├── base_api.py          # Abstract base class
│   │   ├── goodman_api.py       # Goodman adapter
│   │   ├── carrier_api.py       # Carrier adapter
│   │   ├── johnstone_api.py     # Johnstone Supply adapter
│   │   └── ferguson_api.py      # Ferguson adapter
│   └── orchestrator.py          # Coordinates all APIs
│
├── phase2_matching/             # Part matching & enrichment
│   ├── matcher.py               # Part number matching
│   ├── classifier.py            # Zero-shot classification
│   └── enricher.py              # Data enrichment (combines matching + classification)
│
├── data/                        # All data stored here
│   ├── raw/                     # Phase 1 outputs (API responses)
│   │   ├── goodman/
│   │   ├── carrier/
│   │   ├── johnstone/
│   │   ├── ferguson/
│   │   └── consolidated/        # Multi-API search results
│   └── processed/               # Phase 2 outputs (enriched data)
│       └── {part_number}/       # Per-part directories
│
├── tests/                       # Comprehensive test suite
│   ├── test_apis/               # API adapter tests (40 tests)
│   ├── test_matching/           # Matching tests (21 tests)
│   ├── integration/             # Integration tests (17 tests)
│   └── output/                  # All test results saved here
│
├── gui.py                       # Lightweight GUI application
├── demo.py                      # Interactive demonstration
├── run_tests.py                 # Complete test runner
├── requirements.txt             # Minimal dependencies
├── README.md                    # This file
├── QUICKSTART.md               # 5-minute getting started
├── ARCHITECTURE.md             # System design details
├── GUI_GUIDE.md                # GUI user guide
└── TESTING_GUIDE.md            # Comprehensive testing guide
```

---

## Installation

### 1. Clone or navigate to the repository

```bash
cd Elusive_trades_data
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. (Optional) Install transformers for zero-shot classification

If you want to use the AI-powered deprecation/replacement detection:

```bash
pip install transformers torch sentencepiece
```

Or uncomment the relevant lines in `requirements.txt` and reinstall.

---

## Quick Access

### GUI Application

Launch the graphical interface for easy searches:

```bash
python gui.py
```

Features:
- **Part Number Search** - Search across all APIs
- **Model Number Search** - Find parts for equipment models
- **Automatic Enrichment** - Optional Phase 2 data enrichment
- **Save Results** - Export to JSON in `tests/output/`
- **User-Friendly** - No command-line knowledge needed

See [GUI_GUIDE.md](GUI_GUIDE.md) for detailed instructions.

### Run Tests

```bash
# Complete test suite (78 tests)
python run_tests.py

# Unit tests only
pytest

# Integration tests
python tests/integration/test_complex_scenarios.py
```

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for comprehensive testing documentation.

### Interactive Demo

```bash
python demo.py
```

---

## Phase 1: Data Acquisition

### Quick Start

```python
from phase1_acquisition.orchestrator import APIOrchestrator

# Initialize orchestrator
orchestrator = APIOrchestrator()

# Search all APIs for a part
results = orchestrator.search_all_apis("0131M00008P")

# Get detailed information
details = orchestrator.get_part_details_from_all("0131M00008P")

# Search by model number
model_results = orchestrator.search_by_model_all_apis("ARUF37C14")
```

### Adding New APIs

1. Create a new file in `phase1_acquisition/apis/` (e.g., `grainger_api.py`)
2. Inherit from `BaseAPI` and implement required methods:
   - `search_by_part_number(part_number)`
   - `search_by_model(model_number)`
   - `get_part_details(part_id)`
   - `get_available_endpoints()`

3. Add to orchestrator:

```python
from phase1_acquisition.apis.grainger_api import GraingerAPI

orchestrator = APIOrchestrator()
orchestrator.add_api('grainger', GraingerAPI())
```

### Output

All API responses are saved to `data/raw/{api_name}/{timestamp}/` as JSON files.

---

## Phase 2: Matching & Enrichment

### Quick Start

```python
from phase2_matching.enricher import PartEnricher

# Initialize enricher
enricher = PartEnricher()

# Enrich a part (runs matching + classification)
enriched_data = enricher.enrich_part("0131M00008P")

# Access results
print(f"Is Deprecated: {enriched_data['status']['is_deprecated']}")
print(f"Cross References: {enriched_data['relationships']['cross_references']}")
print(f"Replacements: {enriched_data['relationships']['replacements']}")
```

### What Phase 2 Does

1. **Searches Phase 1 data** for the part number across all APIs
2. **Extracts text** from all matching records
3. **Classifies text** using zero-shot learning to detect:
   - Deprecation status (discontinued, obsolete, etc.)
   - Replacement information (replaced by, superseded by, etc.)
   - Compatibility (equivalent to, compatible with, etc.)
4. **Extracts relationships** (cross-references, replacements, compatible parts)
5. **Calculates confidence scores** for all findings
6. **Saves enriched data** to `data/processed/{part_number}/`

### Using Individual Components

**Matcher only:**
```python
from phase2_matching.matcher import PartMatcher

matcher = PartMatcher()
results = matcher.search_part("0131M00008P")
cross_refs = matcher.find_cross_references("0131M00008P")
```

**Classifier only:**
```python
from phase2_matching.classifier import PartStatusClassifier

classifier = PartStatusClassifier()

# Classify text
text = "This part has been discontinued and replaced by part XYZ123"
result = classifier.classify_all(text)

# Extract part numbers
part_numbers = classifier.extract_part_numbers_from_text(text)
```

### Output

Enriched data is saved to `data/processed/{part_number}/enriched_{timestamp}.json`

---

## Running Tests

All components have comprehensive TDD tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=phase1_acquisition --cov=phase2_matching

# Run specific test file
pytest tests/test_apis/test_goodman_api.py

# Run specific test
pytest tests/test_apis/test_base_api.py::TestBaseAPI::test_initialization
```

### Test Structure

- `tests/test_apis/` - Tests for all API adapters
  - `test_base_api.py` - BaseAPI abstract class tests
  - `test_goodman_api.py` - Goodman API tests
  - `test_carrier_api.py` - Carrier API tests
  - `test_orchestrator.py` - Orchestrator tests

- `tests/test_matching/` - Tests for Phase 2
  - `test_matcher.py` - PartMatcher tests
  - `test_classifier.py` - PartStatusClassifier tests

---

## Example Workflow

### Complete Part Search & Enrichment

```python
from phase1_acquisition.orchestrator import APIOrchestrator
from phase2_matching.enricher import PartEnricher

# Phase 1: Acquire data from all APIs
print("Phase 1: Acquiring data from APIs...")
orchestrator = APIOrchestrator()
api_results = orchestrator.search_all_apis("0131M00008P")
print(f"Found data from {len(api_results['results'])} APIs")

# Phase 2: Enrich the data
print("\nPhase 2: Enriching part data...")
enricher = PartEnricher()
enriched = enricher.enrich_part("0131M00008P")

# Display results
print(f"\n=== Results for {enriched['part_number']} ===")
print(f"Data sources: {enriched['data_sources']}")
print(f"Is deprecated: {enriched['status']['is_deprecated']}")
print(f"Has replacement: {enriched['status']['has_replacement']}")
print(f"\nCross-references found: {len(enriched['relationships']['cross_references'])}")
print(f"Replacements found: {len(enriched['relationships']['replacements'])}")
print(f"Compatible parts found: {len(enriched['relationships']['compatible_parts'])}")

print("\nConfidence scores:")
for key, score in enriched['confidence_scores'].items():
    print(f"  {key}: {score:.2%}")
```

---

## API Configuration

### Current Status

All APIs currently return **mock data** for development and testing. To connect to real APIs:

1. Update the `BASE_URL` in each API adapter
2. Implement actual HTTP requests (code is already structured for this)
3. Add authentication if required (no passwords in config - use environment variables)

Example:

```python
# In goodman_api.py
BASE_URL = "https://api.goodmanmfg.com"  # Update this

def search_by_part_number(self, part_number: str):
    endpoint = f"{self.BASE_URL}/parts/search"
    params = {"partNumber": part_number}

    response = self.session.get(endpoint, params=params, timeout=self.timeout)
    response.raise_for_status()
    data = response.json()

    self.save_response(data, f"part_{part_number}")
    return data
```

---

## Zero-Shot Classification

The classifier uses pre-trained transformer models (default: `facebook/bart-large-mnli`) to detect:

- **Deprecation indicators**: "discontinued", "obsolete", "no longer available", "end of life"
- **Replacement indicators**: "replaced by", "superseded by", "alternative", "substitute"
- **Compatibility indicators**: "compatible with", "equivalent to", "interchangeable with"

**No training required** - the model works out of the box on any text.

### Customizing Labels

Edit `phase2_matching/classifier.py`:

```python
class PartStatusClassifier:
    DEPRECATION_LABELS = [
        "discontinued",
        "deprecated",
        "obsolete",
        # Add your custom labels here
    ]
```

### Adjusting Confidence Threshold

```python
# Default threshold is 0.5 (50%)
result = classifier.classify_deprecation_status(text, threshold=0.7)  # More strict
result = classifier.classify_deprecation_status(text, threshold=0.3)  # More permissive
```

---

## Data Storage

### Phase 1 Data (`data/raw/`)

```
data/raw/
├── goodman/
│   └── 20240115_143022/         # Session timestamp
│       ├── part_0131M00008P.json
│       ├── model_ARUF37C14.json
│       └── details_0131M00008P.json
├── carrier/
│   └── 20240115_143022/
│       └── part_P291-4053RS.json
└── consolidated/                 # Multi-API searches
    ├── search_all_0131M00008P_20240115_143022.json
    └── details_all_0131M00008P_20240115_143022.json
```

### Phase 2 Data (`data/processed/`)

```
data/processed/
└── 0131M00008P/                  # Normalized part number
    ├── match_results_20240115_143022.json
    └── enriched_20240115_143022.json
```

---

## Development

### Running Individual Components

**Phase 1 Orchestrator:**
```bash
python phase1_acquisition/orchestrator.py
```

**Phase 2 Matcher:**
```bash
python phase2_matching/matcher.py
```

**Phase 2 Classifier:**
```bash
python phase2_matching/classifier.py
```

**Phase 2 Enricher:**
```bash
python phase2_matching/enricher.py
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 phase1_acquisition phase2_matching

# Type checking
mypy phase1_acquisition phase2_matching
```

---

## Key Design Decisions

### ✅ Why File-Based Storage?

- **Simplicity**: No database setup, no connection management
- **Portability**: Data is just JSON files, easy to move/backup
- **Transparency**: Can inspect data with any text editor
- **Version Control**: Can track data changes with git
- **Debugging**: Easy to trace data flow through the system

### ✅ Why No Docker?

- **Simplicity**: Just Python scripts, no container orchestration
- **Development Speed**: No build/deploy cycle
- **Resource Efficiency**: No container overhead
- **Easier Debugging**: Standard Python debugging tools work

### ✅ Why Zero-Shot Classification?

- **No Training Data Required**: Works immediately on any text
- **Deterministic**: Same input = same output (given same model)
- **Adaptable**: Add new labels without retraining
- **Transparent**: Can see exactly what labels were used

### ✅ Why TDD Tests?

- **Quality Assurance**: Every API and function is tested
- **Regression Prevention**: Changes don't break existing functionality
- **Documentation**: Tests show how to use each component
- **Confidence**: Can refactor safely with test coverage

---

## Troubleshooting

### Tests failing with "transformers not installed"

Install the optional dependencies:
```bash
pip install transformers torch sentencepiece
```

Or skip those tests - the classifier will still work for part number extraction.

### "No data found" when searching

Make sure you've run Phase 1 to acquire data first:
```python
orchestrator = APIOrchestrator()
orchestrator.search_all_apis("0131M00008P")  # Creates data in data/raw/
```

### API returning mock data instead of real data

The API adapters are currently configured with mock responses for development. Update the API implementation to call real endpoints.

---

## Next Steps

1. **Connect to Real APIs**: Update API adapters with actual endpoints and authentication
2. **Expand API Coverage**: Add more suppliers (Grainger, Trane, Lennox, etc.)
3. **Improve Classification**: Fine-tune threshold values based on real data
4. **Add API Caching**: Implement TTL-based caching to reduce API calls
5. **Build CLI Interface**: Add command-line tools for common operations
6. **Add Logging**: Enhanced logging for production deployment

---

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]
