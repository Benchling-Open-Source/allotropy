# Changelog
All notable changes to this packages will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
### Fixed
### Changed
### Deprecated
### Removed
### Security

## [0.1.11] - 2023-12-04
### Added
- Add parser structure documentation
### Changed
- Refactor Agilent Gen5 with explicit dataclasses structure
- Update Benchman Vi-cell Blu adapter to use the new cell-counting BENCHLING/2023/11 schema
- Update Benchman Vi-cell XR adapter to use the new cell-counting BENCHLING/2023/11 schema
- Set mypy's disallow_any_generics to True. Ideally, new files should not suppress these warnings.
- Refactor way to extract and validate information from pandas series in AppBio QuantStudio
- Simplify CSV lines reader
- Update PerkinElmer EnVision adapter to use the new plate-reader BENCHLING/2023/09 schema
- Standaradize and clarify exception messages

## [0.1.10] - 2023-11-14
### Added
- Add data system document to plate reader schema
### Changed
- Redefine reporter dye setting for genotyping experiments in AppBio QuantStudio
- Refactor Moldev Softmax Pro with explicit dataclasses structure
- Inline VendorParser.parse_timestamp (was only used by VendorParser.get_date_time)
- Change TimeStampParser.parse() to raise for invalid input

## [0.1.9] - 2023-11-03
### Added
- Add missing example outputs for AppBio Quantstudio tests
- Add cell-counting REC/2023/09 schema, with additions to support existing use cases
### Fixed
- Update plate-reader schema to be compatible with current supported adapters and change REC -> BENCHLING

## [0.1.8] - 2023-10-30
### Added
- Allow lines reader to accept or infer encoding
### Fixed
- Use fuzzy=True for timestamp parsing to handle non-standard cases (e.g. mixing 24h time and AM/PM)

## [0.1.7] - 2023-10-26
### Added
- Governance document
- Added plate-reader REC/2023/09 schema (not in use by parsers yet)
### Fixed
### Changed
- Relax TimestampParser to use tzinfo for typing
- Change the cell counter schema name to match with the one published by Allotrope (cell counting)
- Update README, CONTRIBUTING, and pyproject.toml
- Rename to PerkinElmerEnvisionParser and RocheCedexBiohtParser for consistency
- Add additional plate reader testing data for the plate reader parser
- Change generic Exceptions to AllotropyErrors

## [0.1.6] - 2023-10-16
### Added
- Test for broken calculated document structure in AppBio QuantStudio
### Fixed
- Fix bug in result caching in AppBio Quantstudio
### Changed
- Allow block type to have plate well count in any position for AppBio QuantStudio
- Replace datetime.timezone with ZoneInfo in TimestampParser
- Implement CsvReader as child of LinesReader

## [0.1.5] - 2023-10-04
### Added
- Parser for AppBio Absoute Q dPCR exports
### Fixed
- Redefine calculated data documents references as required in AppBio QuantStudio parser
- Update dPCR schema "experiement type" enum to have correct values
### Changed
- Make "flourescence intensity threshold setting" optional in the dPCR schema
- Changed the "calculated datum" property on the calculated data documents to allow different units

## [0.1.4] - 2023-10-03
### Fixed
- Remove duplication of calculated documents related to quantity measurements in AppBio QuantStudio
- Rename "qPRC detection chemistry" to "PRC detection chemistry" in PCR schemas
- Add missing @dataclass annotation to TQuantityValueNumberPerMicroliter

## [0.1.3] - 2023-10-03
### Fixed
- Redefine the way calculated documents are structured for relative standard curve in AppBio QuantStudio
- Fixed some issues in dPCR schema and corresponding model updates
- Accept comma as thousand indicator in all sections of AppBio Quantstudio

## [0.1.2] - 2023-09-27
### Added
- Allotrope Simple Model schema for Digital PCR (dPCR) documents
- Calculated documents for the AppBio Quantstudio parser
- Genotyping data structure test for AppBio Quantstudio parser
### Fixed
- Typing ignore tags removed from the construction of AppBio Quantstudio structure
- Ignore unexpected sections in AppBio Quantstudio input file
- Accept comma as thousand indicator in AppBio Quantstudio results section

## [0.1.1] - 2023-09-22
### Changed
- Loosened requirement for jsonschema package to make allotropy compatible with datamodel-code-generator

## [0.1.0] - 2023-09-18
### Added
- Initial commit, includes support for:
  - Agilent Gen5
  - Applied Bio QuantStudio
  - Beckman Vi-Cell BLU
  - Beckman Vi-Cell XR
  - MolDev SoftMax Pro
  - NovaBio Flex2
  - PerkinElmer Envision
  - Roche Cedex BioHT
