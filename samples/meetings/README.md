# Sample Meeting Notes with Ground Truth Labels

This directory contains diverse meeting notes with ground-truth labels for testing and evaluation.

## Structure

Each sample file includes:
- **Content**: Realistic meeting notes in various formats
- **Ground Truth Labels**: YAML frontmatter with structured labels:
  - `themes`: Expected theme IDs and keywords
  - `steps`: Expected step extractions
  - `definitions`: Expected term definitions
  - `faqs`: Expected FAQ pairs
  - `decisions`: Expected decision points
  - `actions`: Expected action items
  - `roles`: Expected role mappings
  - `project`: Project classification

## Usage

```bash
# Use in tests
pytest tests/evaluation/ -v

# Ingest samples
mtm ingest samples/meetings/

# Evaluate against ground truth
mtm evaluate --ground-truth samples/meetings/
```

## File Naming Convention

- Format: `{project}_{date}_{topic}.{ext}`
- Examples:
  - `engineering_20250115_code-review.md`
  - `support_20250116_customer-escalation.txt`
  - `product_20250117_roadmap-planning.docx`

