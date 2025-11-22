# Meeting-to-Modules (MTM)

A knowledge management system that transforms unstructured meeting notes into structured, searchable modules using natural language processing and machine learning.

## Problem Statement

**Challenge 7 Requirements:**

This project addresses the challenge of converting unstructured meeting notes into organized, reusable knowledge modules. The system:

- **Ingests** meeting notes from multiple formats (Markdown, TXT, DOCX, PDF)
- **Preprocesses** content into segments for analysis
- **Analyzes** themes using TF-IDF vectorization and KMeans clustering
- **Extracts** structured information (steps, definitions, FAQs, decisions, actions)
- **Generates** formatted modules using Jinja2 templates
- **Tracks** versions using Semantic Versioning (SemVer)
- **Exports** knowledge bases in multiple formats (CSV, Markdown, PDF)

The system maintains full traceability through backlinks, supports role-based organization, and provides comprehensive search and verification capabilities.

## Screenshots

See [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md) for visual demonstrations of the system.

- [Theme List](docs/images/theme-list.png) - View identified themes
- [Generated Tutorial Module](docs/images/tutorial-module.png) - Example tutorial output
- [Diff View](docs/images/diff-view.png) - Module version comparison
- [Exports Folder](docs/images/exports-folder.png) - Export structure

## Quickstart

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)

### Installation

**Using Make (Recommended):**
```bash
# Clone the repository
git clone <repository-url>
cd Challenge_7

# Install dependencies
make install

# Activate the virtual environment
poetry shell
```

**Using Poetry directly:**
```bash
# Clone the repository
git clone <repository-url>
cd Challenge_7

# Install dependencies
poetry install

# Activate the virtual environment
poetry shell
```

### Basic Usage

**Quick Start (Demo Script):**
```bash
# Run the complete demo pipeline
./scripts/demo.sh
```

**Manual Commands:**
```bash
# Initialize sample data (optional, for testing)
mtm init-sample

# Ingest meeting notes from a directory
mtm ingest data/meeting-notes/

# Preprocess notes into segments
mtm preprocess

# Analyze themes from segments
mtm analyze

# Extract structured information (steps, definitions, etc.)
mtm extract

# Generate modules from templates
mtm generate

# Export knowledge base
mtm export

# Search across notes, segments, and extractions
mtm search "deployment process"

# List themes or modules
mtm list --themes
mtm list --modules

# Verify system integrity
mtm verify
```

### Full Pipeline Example

```bash
# Run the complete pipeline
mtm init-sample
mtm ingest
mtm preprocess
mtm analyze
mtm extract
mtm generate
mtm export
```

### Demo Script

For a quick demonstration, use the provided demo script:

**Using Make (Recommended):**
```bash
# Run the complete demo (cleans outputs, runs pipeline, shows results, verifies)
make demo
```

**Using the script directly:**
```bash
# Run the complete demo (cleans outputs, runs pipeline, shows results)
./scripts/demo.sh
```

The demo script will:
1. Clean existing outputs
2. Initialize sample data
3. Run the complete pipeline (ingest → preprocess → analyze → extract → generate → export)
4. Display summary counts (notes, themes, modules, files)
5. Open the generated index file (if available)
6. Show path hints for exploring results
7. Run verification checks (when using `make demo`)

**Note**: 
- On Linux/macOS: The script is executable and can be run directly
- On Windows: Use Git Bash or WSL to run the script, or run the commands manually following the "Full Pipeline Example" above
- To make the script executable on Linux/macOS: `chmod +x scripts/demo.sh`

### Pipeline Execution Summary

The following table shows the results of executing the complete pipeline on sample data:

| Step | Command | Status | Output |
|------|---------|--------|--------|
| 1. Initialize Sample Data | `mtm init-sample --count 10` | ✅ Success | Generated 10 sample notes across 3 projects (Onboarding, Deployment, Support) |
| 2. Ingest Notes | `mtm ingest` | ✅ Success | Ingested notes from data/seed/notes/ (Markdown, TXT, DOCX, PDF formats) |
| 3. Preprocess | `mtm preprocess <file>` | ✅ Success | Created segments from ingested notes |
| 4. Analyze Themes | `mtm analyze` | ✅ Success | Identified themes using TF-IDF and KMeans clustering |
| 5. Extract Information | `mtm extract` | ✅ Success | Extracted steps, definitions, FAQs, decisions, and actions |
| 6. Generate Modules | `mtm generate` | ✅ Success | Generated Markdown modules using Jinja2 templates |
| 7. Export | `mtm export --no-pdf` | ✅ Success | Created timestamped export with CSVs and Markdown files |
| 8. Verify | `mtm verify` | ✅ Success | All verification checks passed |

**Pipeline Status**: ✅ **All steps completed successfully**

The pipeline processes meeting notes through ingestion, preprocessing, theme analysis, structured extraction, module generation, and export, with comprehensive verification at each stage.

**Visual Examples**: See [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md) for screenshots of the pipeline outputs.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Input Layer                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │   .md    │  │   .txt   │  │  .docx   │  │   .pdf   │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │             │              │              │             │
│       └─────────────┴──────────────┴──────────────┘             │
│                            │                                    │
│                    ┌───────▼────────┐                          │
│                    │   Ingest       │                          │
│                    │   (Parsers)    │                          │
│                    └───────┬────────┘                          │
└────────────────────────────┼────────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │   SQLite DB      │
                    │   (Notes Table)  │
                    └────────┬─────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                    ┌───────▼────────┐                          │
│                    │  Preprocess    │                          │
│                    │  (Segmentation)│                          │
│                    └───────┬────────┘                          │
│                             │                                    │
│                    ┌────────▼─────────┐                       │
│                    │   SQLite DB       │                       │
│                    │  (Segments Table) │                       │
│                    └────────┬─────────┘                       │
│                             │                                    │
│                    ┌───────▼────────┐                          │
│                    │    Analyze      │                          │
│                    │  (TF-IDF +      │                          │
│                    │   KMeans)       │                          │
│                    └───────┬────────┘                          │
│                             │                                    │
│                    ┌────────▼─────────┐                       │
│                    │   SQLite DB      │                       │
│                    │  (Themes Table)  │                       │
│                    │ (Role Mappings)   │                       │
│                    └────────┬─────────┘                       │
│                             │                                    │
│                    ┌───────▼────────┐                          │
│                    │    Extract      │                          │
│                    │  (LLM-based)    │                          │
│                    └───────┬────────┘                          │
│                             │                                    │
│                    ┌────────▼─────────┐                       │
│                    │   SQLite DB      │                       │
│                    │(Extractions Table)│                      │
│                    └────────┬─────────┘                       │
│                             │                                    │
│                    ┌───────▼────────┐                          │
│                    │   Generate     │                          │
│                    │  (Jinja2)     │                          │
│                    └───────┬────────┘                          │
│                             │                                    │
│                    ┌────────▼─────────┐                       │
│                    │   SQLite DB      │                       │
│                    │ (Modules Table)  │                       │
│                    │ (Versions Table) │                       │
│                    └────────┬─────────┘                       │
│                             │                                    │
│                    ┌───────▼────────┐                          │
│                    │    Export      │                          │
│                    │ (CSV, MD, PDF)│                          │
│                    └────────┬────────┘                          │
└────────────────────────────┼────────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │  Output Files     │
                    │  outputs/         │
                    │  ├── modules/     │
                    │  ├── exports/     │
                    │  └── logs/        │
                    └───────────────────┘
```

### Key Components

1. **Ingest Layer**: Parsers for Markdown, TXT, DOCX, and PDF files
2. **Preprocess Layer**: Text segmentation and cleaning
3. **Analysis Layer**: TF-IDF vectorization and KMeans clustering for theme identification
4. **Extraction Layer**: LLM-based extraction of structured information
5. **Generation Layer**: Jinja2 template rendering for module creation
6. **Storage Layer**: SQLite database with full schema and relationships
7. **Export Layer**: Multi-format export (CSV, Markdown, PDF)

**Visual Overview**: See [Theme List](docs/images/theme-list.png) and [Generated Tutorial Module](docs/images/tutorial-module.png) for examples of the analysis and generation outputs.

## Data Schema

### Core Tables

#### `notes`
Primary table for ingested meeting notes.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `project` | TEXT | Project name |
| `date` | TEXT | ISO format datetime |
| `source_file` | TEXT | Original filename |
| `line_start` | INTEGER | Start line in source |
| `line_end` | INTEGER | End line in source |
| `content` | TEXT | Full note content |
| `title` | TEXT | Note title |
| `metadata` | TEXT | JSON string of metadata |
| `content_sha256` | TEXT | SHA256 hash for duplicate detection |
| `source_path` | TEXT | Full file path |
| `mtime` | TEXT | File modification time |
| `size` | INTEGER | File size in bytes |
| `created_at` | TEXT | Creation timestamp |
| `updated_at` | TEXT | Update timestamp |

**Indexes**: `project`, `date`, `source_file`, `content_sha256`

#### `segments`
Text segments extracted from notes.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `note_id` | UUID (FK) | Reference to notes.id |
| `project` | TEXT | Project name |
| `date` | TEXT | ISO format datetime |
| `source_file` | TEXT | Source filename |
| `line_start` | INTEGER | Start line |
| `line_end` | INTEGER | End line |
| `content` | TEXT | Segment content |
| `segment_type` | TEXT | Type (paragraph, list, quote) |
| `order` | INTEGER | Order within note |
| `created_at` | TEXT | Creation timestamp |
| `updated_at` | TEXT | Update timestamp |

**Indexes**: `note_id`, `project`, `date`

#### `themes`
Themes identified through clustering.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `project` | TEXT | Project name |
| `name` | TEXT | Theme name |
| `description` | TEXT | Theme description |
| `keywords` | TEXT | JSON array of keywords |
| `support_count` | INTEGER | Number of supporting documents |
| `note_id` | UUID (FK) | Reference to notes.id |
| `created_at` | TEXT | Creation timestamp |
| `updated_at` | TEXT | Update timestamp |

**Indexes**: `project`, `name`

#### `extractions`
Polymorphic table for structured extractions.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `type` | TEXT | step, definition, faq, decision, action, topic |
| `project` | TEXT | Project name |
| `payload` | TEXT | JSON string of extraction data |
| `note_id` | UUID (FK) | Reference to notes.id |
| `segment_ids` | TEXT | JSON array of segment UUIDs |
| `source_file` | TEXT | Source filename |
| `line_start` | INTEGER | Start line |
| `line_end` | INTEGER | End line |
| `date` | TEXT | ISO format datetime |
| `created_at` | TEXT | Creation timestamp |
| `updated_at` | TEXT | Update timestamp |

**Indexes**: `type`, `project`, `note_id`

#### `modules`
Generated knowledge modules.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `project` | TEXT | Project name |
| `title` | TEXT | Module title |
| `description` | TEXT | Module description |
| `module_type` | TEXT | tutorial, faq, howto, role_path, index |
| `content` | TEXT | Generated content |
| `theme_ids` | TEXT | JSON array of theme UUIDs |
| `step_ids` | TEXT | JSON array of step UUIDs |
| `definition_ids` | TEXT | JSON array of definition UUIDs |
| `faq_ids` | TEXT | JSON array of FAQ UUIDs |
| `decision_ids` | TEXT | JSON array of decision UUIDs |
| `action_ids` | TEXT | JSON array of action UUIDs |
| `version` | INTEGER | SemVer-encoded version |
| `created_at` | TEXT | Creation timestamp |
| `updated_at` | TEXT | Update timestamp |

**Indexes**: `project`, `module_type`

#### `versions`
Version history for modules.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `module_id` | UUID (FK) | Reference to modules.id |
| `version` | INTEGER | SemVer-encoded version |
| `project` | TEXT | Project name |
| `title` | TEXT | Module title |
| `description` | TEXT | Module description |
| `content` | TEXT | Module content |
| `changes` | TEXT | Description of changes |
| `created_by` | TEXT | Creator identifier |
| `created_at` | TEXT | Creation timestamp |

**Indexes**: `module_id`, `version`

#### `topic_role_map`
Mapping between themes/topics and roles.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `topic_id` | UUID | Theme or topic UUID |
| `role` | TEXT | Role name |
| `confidence` | REAL | Mapping confidence (0-1) |
| `created_at` | TEXT | Creation timestamp |

**Indexes**: `topic_id`, `role`

#### `runs`
Processing run tracking.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `run_type` | TEXT | Type of run (ingest, analyze, etc.) |
| `project` | TEXT | Project name |
| `status` | TEXT | started, completed, failed |
| `input_files` | TEXT | JSON array of input files |
| `output_files` | TEXT | JSON array of output files |
| `config` | TEXT | JSON string of configuration |
| `error` | TEXT | Error message if failed |
| `started_at` | TEXT | Start timestamp |
| `completed_at` | TEXT | Completion timestamp |
| `created_at` | TEXT | Creation timestamp |

## Configuration Reference

Configuration is stored in `configs/config.toml` (TOML format).

### Configuration Options

```toml
[mtm]
# Input directories for meeting notes
input_dirs = ["data/seed/notes"]

# Output directory for generated files
output_dir = "outputs"

# Database path
db_path = "outputs/mtm.db"

# Language for processing
language = "en"

# Theme analysis settings
min_theme_support = 3  # Minimum segments per theme
kmeans_k = 6           # Number of clusters for KMeans

# Optional: Path to redaction rules file
redact_rules = null

# Role taxonomy identifier
role_taxonomy = "default"

# Enable PDF to text conversion
enable_pdf_to_text = true
```

### Environment Variables

- `MTM_CONFIG_PATH`: Override default config file path
- `MTM_DB_PATH`: Override database path

## Templates Guide

Templates are Jinja2 files located in `src/mtm/generate/templates/`.

**Example Output**: See [Generated Tutorial Module](docs/images/tutorial-module.png) for a rendered example.

### Available Templates

1. **`tutorial.md.j2`**: Step-by-step tutorials
2. **`faq.md.j2`**: Frequently asked questions
3. **`howto.md.j2`**: How-to guides
4. **`role_path.md.j2`**: Role-specific learning paths
5. **`index.md.j2`**: Project and global indexes

### Template Variables

All templates receive the following context:

- `title`: Module title
- `description`: Module description
- `project`: Project name
- `module_type`: Type of module
- `last_updated`: Last update timestamp
- `version`: SemVer version
- `toc`: Table of contents (list of `{title, anchor}`)
- `steps`: List of step objects
- `definitions`: List of definition objects
- `faqs`: List of FAQ objects
- `decisions`: List of decision objects
- `actions`: List of action objects
- `themes`: List of theme objects
- `backlinks`: `{note_id, segment_ids}`
- `counts`: `{steps, definitions, faqs, decisions, actions, themes}`
- `role`: Role name (for role_path templates)

### Customizing Templates

1. Edit template files in `src/mtm/generate/templates/`
2. Use Jinja2 syntax for conditionals, loops, and filters
3. Templates support Markdown formatting
4. Run `mtm generate` to regenerate modules

### Example Template Structure

```jinja2
# {{ title }}

{% if description %}
{{ description }}
{% endif %}

## Table of Contents
{% for item in toc %}
- [{{ item.title }}](#{{ item.anchor }})
{% endfor %}

---

**Project:** {{ project }}
**Last Updated:** {{ last_updated }}
**Version:** {{ version }}

{% if steps %}
## Steps
{% for step in steps %}
### {{ step.step_number }}. {{ step.title }}
{{ step.description }}
{% endfor %}
{% endif %}
```

## Troubleshooting

### NLTK Data Download

If you encounter errors about missing NLTK data:

```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

Or programmatically in Python:

```python
import nltk
nltk.download('punkt')
nltk.download('stopwords')
```

### Pandoc Not Found

PDF export requires `pandoc`. If not installed:

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install pandoc
```

**macOS:**
```bash
brew install pandoc
```

**Windows:**
Download from [pandoc.org/installing.html](https://pandoc.org/installing.html)

The system will gracefully skip PDF conversion if `pandoc` is not available.

### Database Locked Errors

If you see "database is locked" errors:

1. Ensure no other processes are accessing the database
2. Check for stale lock files in the database directory
3. Restart the application

### Theme Analysis Produces No Results

If `mtm analyze` produces no themes:

1. Check that segments exist: `mtm verify`
2. Reduce `min_theme_support` in config (default: 3)
3. Adjust `kmeans_k` to match your data size
4. Ensure notes contain sufficient content

### Import Errors

If you see import errors:

```bash
# Reinstall dependencies
poetry install --sync

# Verify Python version
python --version  # Should be 3.11+
```

### Permission Errors

If you encounter permission errors:

1. Check file/directory permissions
2. Ensure write access to `outputs/` directory
3. On Windows, run as administrator if needed

## Development

### Using Makefile

The project includes a Makefile with convenient targets:

```bash
# Show all available targets
make help

# Install dependencies
make install

# Run linting
make lint

# Run type checking
make typecheck

# Run tests
make test

# Run tests with coverage
make test-cov

# Run integration tests
make test-integration

# Run all CI checks
make ci

# Run pre-commit checks (lint-fix, format, typecheck)
make pre-commit

# Clean generated files
make clean

# Run demo
make demo
```

### Running Tests

**Using Make:**
```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run integration tests
make test-integration

# Run unit tests
make test-unit
```

**Using Poetry directly:**
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src/mtm --cov-report=html

# Run integration tests
poetry run pytest tests/integration/ -v

# Run specific test
poetry run pytest tests/integration/test_full_pipeline.py -v
```

### Code Quality

**Using Make:**
```bash
# Linting
make lint

# Format code
make format

# Check formatting
make format-check

# Type checking
make typecheck

# Auto-fix linting issues
make lint-fix
```

**Using Poetry directly:**
```bash
# Linting
poetry run ruff check .

# Formatting
poetry run ruff format .

# Type checking
poetry run mypy src/mtm
```

### CI/CD

The project includes GitHub Actions workflows for:
- Linting (Ruff)
- Type checking (MyPy)
- Testing (Pytest)
- Coverage reporting (minimum 80%)

## Documentation

- [Screenshots](docs/SCREENSHOTS.md) - Visual demonstrations of features
- [Changelog](CHANGELOG.md) - Version history and changes
- [Code of Conduct](CODE_OF_CONDUCT.md) - Community guidelines

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed list of changes and version history.

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for our Contributor Covenant Code of Conduct.

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

Examples of behavior that contributes to creating a positive environment include:

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

Examples of unacceptable behavior include:

- The use of sexualized language or imagery
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate in a professional setting

### Enforcement

Project maintainers are responsible for clarifying and enforcing our standards of acceptable behavior and will take appropriate and fair corrective action in response to any instances of unacceptable behavior.

### Attribution

This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org), version 2.1.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Ensure all tests pass and coverage is maintained
6. Submit a pull request

## Support

For issues, questions, or contributions, please open an issue on the repository.

---

**Version**: 0.1.0  
**Python**: 3.11+  
**License**: MIT
