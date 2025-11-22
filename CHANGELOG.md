# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of Meeting-to-Modules (MTM) system
- Support for ingesting multiple file formats (Markdown, TXT, DOCX, PDF)
- Text preprocessing and segmentation
- Theme analysis using TF-IDF vectorization and KMeans clustering
- Structured information extraction (steps, definitions, FAQs, decisions, actions)
- Module generation using Jinja2 templates
- Version tracking with Semantic Versioning (SemVer)
- Knowledge base export (CSV, Markdown, PDF)
- Full-text search across notes, segments, and extractions
- Role-based organization and mapping
- Comprehensive verification system
- Structured logging with Rich
- Integration tests with golden file comparison
- Demo script for quick pipeline demonstration
- Makefile for development workflows
- CI/CD pipeline with GitHub Actions
- Comprehensive documentation (README, templates guide, troubleshooting)

### Changed
- N/A (Initial release)

### Deprecated
- N/A (Initial release)

### Removed
- N/A (Initial release)

### Fixed
- N/A (Initial release)

### Security
- N/A (Initial release)

## [0.1.0] - 2025-11-21

### Added
- Initial project structure
- Core data models (Note, Segment, Theme, Step, Definition, FAQ, Decision, Action, Module)
- Database schema with SQLite
- CLI interface with Typer
- Configuration management
- Template system for module generation
- Versioning system with changelog generation
- Export functionality with multiple formats
- Sample data generation
- Search and verification capabilities
- Integration and unit tests
- Documentation and examples

[Unreleased]: https://github.com/yourusername/meeting-to-modules/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/meeting-to-modules/releases/tag/v0.1.0

