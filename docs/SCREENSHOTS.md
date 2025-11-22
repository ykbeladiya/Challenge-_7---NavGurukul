# Screenshots Guide

This document describes the screenshots available for the Meeting-to-Modules project.

## Theme List

**File**: `images/theme-list.png`

Shows the output of the `mtm list --themes` command, displaying a formatted table with:
- Theme IDs (truncated for display)
- Project names
- Top 5 keywords/terms per theme
- Support counts (number of segments supporting each theme)

**How to capture**:
```bash
mtm list --themes
# Capture the terminal output showing the themes table
```

## Generated Tutorial Module

**File**: `images/tutorial-module.png`

Shows a generated tutorial module in Markdown format, typically located in `outputs/modules/<project>/<role>/<theme>/tutorial.md`.

The screenshot should show:
- Module title and description
- Table of contents with anchor links
- Step-by-step instructions
- Definitions and FAQs sections
- Backlinks to source notes
- Version and last updated information

**How to capture**:
```bash
mtm generate
# Open a generated tutorial module in outputs/modules/
# Capture the rendered Markdown content
```

## Diff View

**File**: `images/diff-view.png`

Shows the output of the `mtm diff` command comparing two module versions.

The screenshot should display:
- Unified diff format with context lines
- Added lines (marked with +)
- Removed lines (marked with -)
- Context lines for reference
- File paths being compared

**How to capture**:
```bash
mtm diff <module_id1> <module_id2> --format markdown
# Or compare two files:
mtm diff file1.md file2.md
# Capture the diff output
```

## Exports Folder

**File**: `images/exports-folder.png`

Shows the structure of the exports directory after running `mtm export`.

The screenshot should display:
- Timestamped export folder (e.g., `2025-11-21_14-30-00/`)
- CSV files: `steps.csv`, `definitions.csv`, `faqs.csv`, `decisions.csv`, `actions.csv`, `themes.csv`
- `modules/` directory with generated Markdown files
- `README.md` with export information
- Optional PDF files if pandoc is available

**How to capture**:
```bash
mtm export
# Navigate to outputs/exports/
# Capture the folder structure and file listing
```

## Screenshot Requirements

- **Format**: PNG or JPG
- **Resolution**: Minimum 1280x720 for clarity
- **File size**: Keep under 1MB per image
- **Naming**: Use kebab-case (e.g., `theme-list.png`)
- **Content**: Should clearly show the feature being demonstrated

## Adding New Screenshots

1. Capture the screenshot using your preferred tool
2. Save it in `docs/images/` with a descriptive name
3. Update this file with a description
4. Add a link in the main README.md

