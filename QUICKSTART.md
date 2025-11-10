# Quick Start Guide

Get up and running with the HVAC Parts Search System in under 5 minutes.

## Installation

```bash
# 1. Navigate to the project
cd Elusive_trades_data

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Install AI classification support
pip install transformers torch
```

## Run Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov
```

**Result:** All 53 tests should pass ✓

## Quick Demo

### Option 1: Run the Demo Script

```bash
python demo.py
```

This interactive demo shows:
- Phase 1: API data acquisition
- Phase 2: Part matching and enrichment
- Individual component examples

### Option 2: Python Interactive

```python
from phase1_acquisition.orchestrator import APIOrchestrator

# Initialize and search
orchestrator = APIOrchestrator()
results = orchestrator.search_all_apis("0131M00008P")

# View results
print(f"Found data from {len(results['results'])} APIs")
for api_name, result in results['results'].items():
    print(f"{api_name}: {result['status']}")
```

## What You Get

### Phase 1: API Data
All API responses saved to `data/raw/`:

```
data/raw/
├── goodman/20251110_144652/
│   └── part_0131M00008P.json
├── carrier/20251110_144652/
│   └── part_0131M00008P.json
├── johnstone/20251110_144652/
│   └── part_0131M00008P.json
├── ferguson/20251110_144652/
│   └── part_0131M00008P.json
└── consolidated/
    └── search_all_0131M00008P_20251110_144652.json
```

### Phase 2: Enriched Data
Processed data saved to `data/processed/`:

```
data/processed/
└── 0131M00008P/
    ├── match_results_20251110_144652.json
    └── enriched_20251110_144652.json
```

## Example Workflow

### Search for a Part

```python
from phase1_acquisition.orchestrator import APIOrchestrator
from phase2_matching.enricher import PartEnricher

# Phase 1: Get data from APIs
orchestrator = APIOrchestrator()
api_data = orchestrator.search_all_apis("0131M00008P")

# Phase 2: Enrich the data
enricher = PartEnricher()
enriched = enricher.enrich_part("0131M00008P")

# View results
print(f"Is deprecated: {enriched['status']['is_deprecated']}")
print(f"Cross-references: {len(enriched['relationships']['cross_references'])}")
print(f"Confidence: {enriched['confidence_scores']['data_availability']:.2%}")
```

### Search by Model

```python
orchestrator = APIOrchestrator()
model_data = orchestrator.search_by_model_all_apis("ARUF37C14")

# See which APIs have data for this model
for api_name, result in model_data['results'].items():
    if result['status'] == 'success':
        print(f"{api_name} has data for this model")
```

### Find Cross-References

```python
from phase2_matching.matcher import PartMatcher

matcher = PartMatcher()
cross_refs = matcher.find_cross_references("0131M00008P")

print(f"Found {cross_refs['total_found']} cross-references")
for ref in cross_refs['cross_references']:
    print(f"  {ref['manufacturer']}: {ref['part_number']}")
```

### Classify Text

```python
from phase2_matching.classifier import PartStatusClassifier

classifier = PartStatusClassifier()

# Extract part numbers from text
text = "Compatible with parts 0131M00008P and P291-4053RS"
parts = classifier.extract_part_numbers_from_text(text)
print(f"Found parts: {parts}")

# Classify deprecation (requires transformers)
text = "This part has been discontinued"
result = classifier.classify_deprecation_status(text)
print(f"Is deprecated: {result['is_deprecated']}")
```

## Verify Installation

Run this quick verification:

```python
from phase1_acquisition.orchestrator import APIOrchestrator

orchestrator = APIOrchestrator()
api_info = orchestrator.get_api_info()

print(f"✓ {api_info['total_apis']} API adapters loaded:")
for api_name in api_info['apis'].keys():
    print(f"  - {api_name}")
```

Expected output:
```
✓ 4 API adapters loaded:
  - goodman
  - carrier
  - johnstone
  - ferguson
```

## Current Status

### Working ✓
- ✅ All 4 API adapters (Goodman, Carrier, Johnstone, Ferguson)
- ✅ Multi-API orchestration
- ✅ File-based data storage
- ✅ Part number matching
- ✅ Cross-reference detection
- ✅ Part number extraction
- ✅ TDD test coverage (53 tests)

### Mock Data ⚠️
All APIs currently return **mock data** for development/testing.

To connect to real APIs:
1. Update `BASE_URL` in each API adapter
2. Implement actual HTTP requests
3. Add authentication if needed

### Optional Features
- **Zero-shot classification**: Requires `transformers` and `torch`
  - Install with: `pip install transformers torch`
  - Used for detecting deprecation, replacement, and compatibility info

## File Structure

```
Elusive_trades_data/
├── phase1_acquisition/      # API data collection
│   ├── apis/                # Individual API adapters
│   └── orchestrator.py      # Multi-API coordinator
├── phase2_matching/         # Data enrichment
│   ├── matcher.py           # Part matching
│   ├── classifier.py        # Zero-shot classification
│   └── enricher.py          # Complete enrichment
├── tests/                   # TDD tests
├── data/                    # All output data (created on first run)
├── demo.py                  # Interactive demo
└── README.md                # Full documentation
```

## Next Steps

1. **Explore the code**: Start with [phase1_acquisition/apis/base_api.py](phase1_acquisition/apis/base_api.py)
2. **Add new APIs**: Copy an existing adapter and modify
3. **Connect real endpoints**: Update BASE_URL and implement authentication
4. **Customize classification**: Edit labels in [phase2_matching/classifier.py](phase2_matching/classifier.py)

## Troubleshooting

**Tests failing?**
```bash
# Make sure you're in the project directory
cd Elusive_trades_data

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest
```

**Import errors?**
Make sure you're running from the project root directory.

**Missing transformers?**
This is optional. For basic functionality (API calls, matching), you don't need it.

## Get Help

- See [README.md](README.md) for full documentation
- Check test files in `tests/` for usage examples
- Run `python demo.py` for interactive demonstration

---

**Ready to start?** → `python demo.py`
