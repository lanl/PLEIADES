# Changelog

All notable changes to PLEIADES will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Branch protection rules for main, qa, and next branches

### Changed
- Updated GitHub Actions dependencies (actions/checkout v4→v5, setup-pixi v0.8.5→v0.9.1)

## [2.0.0] - 2025-10-03

### Added
- Modern `src/` directory structure following Python packaging best practices
- Pixi package manager support for better scientific computing workflows
- Comprehensive test suite with 1078 tests and 78% code coverage
- JSON mode support for SAMMY multi-isotope fitting
- ORNL VENUS instrument data processing support
- Nexus/HDF5 file format support
- Pre-commit hooks for code quality
- GitHub Actions CI/CD pipelines for testing and packaging
- Three-branch git-flow structure (next → qa → main)
- Modular architecture with clear separation of concerns:
  - `src/pleiades/nuclear/` - Nuclear data management
  - `src/pleiades/sammy/` - SAMMY integration and I/O
  - `src/pleiades/processing/` - Data processing and normalization
  - `src/pleiades/utils/` - Utility functions

### Changed
- **BREAKING**: Complete project restructure - imports and APIs have changed
- Migrated from Poetry to Pixi for dependency management
- Moved old code to `legacy/` directory for reference
- Improved SAMMY input/output file parsing
- Enhanced resonance parameter handling
- Updated documentation to reflect new architecture
- Default branch changed from `main` to `next`

### Removed
- Poetry dependency management files (`poetry.lock`, old `pyproject.toml` structure)
- Large binary cross-section files from `nucDataLibs/xSections/` (moved to external storage)
- Old flat package structure at root level

### Fixed
- Numerous bugs in SAMMY parameter file parsing
- Data normalization edge cases
- Test coverage gaps

## [0.1.0] - 2024-07-11

### Added
- Initial release of PLEIADES
- Basic SAMMY integration functionality
- Nuclear data retrieval from ENDF
- Simple transmission fitting capabilities
- Basic documentation
- Poetry-based dependency management

### Known Issues
- Limited test coverage
- Flat package structure at root level
- Large binary files in repository

## Links
- [Compare v2.0.0...HEAD](https://github.com/lanl/PLEIADES/compare/v2.0...HEAD)
- [Compare v0.1.0...v2.0.0](https://github.com/lanl/PLEIADES/compare/v0.1...v2.0)

[Unreleased]: https://github.com/lanl/PLEIADES/compare/v2.0...HEAD
[2.0.0]: https://github.com/lanl/PLEIADES/compare/v0.1...v2.0
[0.1.0]: https://github.com/lanl/PLEIADES/releases/tag/v0.1
