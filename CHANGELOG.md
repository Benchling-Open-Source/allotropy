# Changelog

All notable changes to this packages will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.61] - 2024-10-16

### Added

- AppBio QuantStudio Design & Analysis - add xls support and additional filter check for empty stage number column (#724)

### Removed

- MolDev SoftMax Pro - report non numeric values in error document (#725)

## [0.1.60] - 2024-10-15

### Added

- Agilent Tapestation Analysis & Electrophoresis - add electrophoresis/BENCHLING/2024/09 schema and mapper and update parser to use it (#715)
- Solution Analyzer - add solution-analyzer/rec/2024/09 schema mapper (#714)
- MolDev SoftMax Pro - report non numeric values in error document (#713)

## [0.1.59] - 2024-10-11

### Added

- Thermo SkanIt & Revvity Matrix - update adapters release statuses to RECOMMENDED (#719)

### Fixed

- AppBio Quantstudio - remove omitted wells from calculated data document data sources (#717)

## [0.1.58] - 2024-10-09

### Fixed

- ThermoFisher Qubit Flex - add fields that were accidentally removed/renamed in refactor (#711)

## [0.1.57] - 2024-10-09

### Added

- Revvity Kaleido - add v3.5 to supported software versions (#707)
- Solution Analyzer - add solution-analyzer/REC/2024/09 (#706)
- AppBio Quantstudio - support skipping wells that have no results in the raw data file, indicating an omitted well (#689)
- AppBio Quantstudio - add "quantity" calculated data documents for non-STANDARD wells (#698)
- Plate Reader - update adapters using plate-reader/2024/06 schema to include ASM file identifier (#695)
- NanoDrop 8000 & NanoDrop Eight - support alternative reporting format for absorbance measurements (#688)
- Agilent Gen5 - add support for error documents in the  (#694)
- Electrophoresis - add the electrophoresis/REC/2024/06 schema (#693)
- Methodical Mind - update to use plate-reader/REC/2024/06 schema (#692)
- Agilent Gen5 Image - add support for no result sections file examples (#679)
- ThermoSkanIt - initial implementation (#658)
- Perkin Elmer Envision - update to use plate-reader/REC/2024/06 schema (#686)
- BMG Mars - update to use plate-reader/REC/2024/06 schema (#685)
- Spectrophotometry - add spectrophotometry/REC/2024/06 schema (#684)
- Nanodrop Eight - initial implementation (#683)
- Unchained Labs Lunatic - add additional metadata from header block (#680)

### Fixed

- MolDev Softmax Pro - raise error for unsupported Group data format (#696)
- Agilent Gen5 - raise error when there are calculated data but no measurements in results (#691)
- Beckman VI-Cell BLU - filter NaN values when reading cell counts (#687)
- Update DataSeries to use float parsing utility when reading a float value, in order to better handle edge cases (#682)

### Changed

- ThermoFisher Qubit Flex - refactor parser to use schema mapper design pattern (#699)
- All parsers - change the way custom information is organized in schema mappers and ASM outputs to be consistent with future expectations of ASM (#673)
- Thermo Fisher NanoDrop 8000 & Nanodrop EIght - rebrand NanoDrop Eight parser to NanoDrop 8000 (#652)

## [0.1.56] - 2024-09-26

### Added

- AppBio Quantstuido Design and Analysis - add Amp score and Cq confidence calculated data documents (#670)
- MolDev Softmax Pro - add support for kinetic measurements files (#674)
- Revvity Matrix - initial implementation (#656)

### Fixed

- AppBio Quantstuido Design and Analysis - fix Y-intercept and Slope references as data sources for quantity calculated data document (#670)

## [0.1.55] - 2024-09-26

### Added

- AppBio Quantstuido - add cache decorator to amp score calculated data construction (#666)
- Chemometec NC View - initial implementation (#665)

### Fixed

- PCR - mark "PCR Detection Chemistry" as optional in PCR schema (#668)
- Perkin Elmer Envision - remove leading '0' from well identifier numbers (#671)

## [0.1.54] - 2024-09-23

### Added

- AppBio Quantstuido - add additional metadata fields (#661)

### Fixed

- Unchained Labs Lunatic - handle missing 'Sample name' and missing 'Table' label before table parser (#660)
- Agilent Gen5 - cast measurement label to string, since it can numeric when reading directly from dataframe (e.g. a single wavelength) (#657)

### Changed

- Appbio QuantStudio Design & Analysis - simplify sheets needed to infer presence/absence experiment type inference (#659)
- Appbio QuantStudio Design & Analysis - allow software name and version to be None (#659)

## [0.1.53] - 2024-09-17

### Added

- Appbio Quantstudio - add Amp score and Cq conf calculated documents (#670)
- Appbio Quantstudio - add custom information to processed data document (#645)
- Plate Reader - add schema mapper for plate-reader/REC/2024/06 schema (#642)
- Appbio Quantstudio - add checks for missing well item amplification and results data in quantstudio (#643)
- ThermoFisher Nanodrop One - add support for CSV files (#649)
- Thermo SkanIt - initial implementation (#658)
- Agilent Gen5 - add support for label format "[excitation wavelength], [emission wavelength]" for fluorescence point detection (#650)

### Fixed

- Appbio Quantstudio - fix bad reference for y-intercept and slope in quantity calculated data document (#670)
- MolDev Softmax Pro - correctly format timezone (#642)

### Changed

- MolDev Softmax Pro - refactor to use the schema mapper (#642)
- Agilent Gen5 - update to use plate-reader/REC/2024/06 schema (#633)
- Thermo Fisher Genesys30 - update release state to RECOMMENDED (#654)

## [0.1.52] - 2024-09-12

### Fixed

- Roche Cedex Bioht, Thermo Qubit 4 & Flex - fix bug where name of contents instead of contents was being passed to reader (#648)

### Changed

- All parsers - use dateutil timezone instead of pytz, because pytz can create incorrect timezones when not localized (#644)

## [0.1.51] - 2024-09-09

### Added

- MolDev Softmax Pro - add error message for zero plate reader documents (#635)
- AppBio Quantstudio - update data sources for quantity calculated documents with y-intercept and Slope (#630)

### Fixed

- All parsers - allow try_int to handle decimal point in int values (e.g. 1.0) (#638)

### Changed

- MolDev Softmax Pro - update to plate-reader/REC/2024/06 schema (#627)
- MolDev Softmax Pro - remove `NaN` measurements from Softmax Pro adapter to comply with the new `REC` schema (#627)
- Unchained Labs Lunatic - change reader so that it supports both formats (with/without header) for both file types (#631)
- MolDev Softmax Pro - disregard compartment temperature when is reported as 0 (#635)

## [0.1.50] - 2024-08-30

### Added

- All parsers - add `supported_extensions` to Vendor, allowing parsers to specify supported file extensions (#617)
- Agilent Gen5 - add support for multiple read modes (#624)
- Thermo Fisher Nanodrop One - initial implementation

### Fixed

- Mabtech Apex - update regex to handle scenarios where first word in the machine ID section has all letter uppercase

## [0.1.49] - 2024-08-21

### Added

- AppBio QuantStudio Design & Analysis - add primary analysis experiment type
- ThermoFisher Genesys 30 - initial implementation
- Unchained Lunatic - add support for xlsx exports in
- All parsers - add column special character normalization to pandas util

### Fixed

- MolDev SoftMax Pro - fix case where some columns were incorrectly identified as not numeric for calculated data documents. Added exceptions for Masked and Range values which will be treated as NaN.

### Changed
- Spectrophotometry - updated the schema mapper to accommodate absorbance spectrum data cubes

## [0.1.48] - 2024-08-15

### Changed

- BMG MARS - updated release state to RECOMMENDED
- Roche NovaBio Flex2 - update to use solution-analyzer/REC/2024/03 schema

## [0.1.47] - 2024-08-13

### Fixed

- Roche Cedex Bioht - fix mis-reporting some analyte units

## [0.1.46] - 2024-08-13

### Added

- Bio-Rad Bio-Plex Manager - add plate id field
- Spectrophotometry - add luminescence point detection, absorption spectrum detection, fluorescence emission detection measurement extension to spectrophotometry/BENCHLING/2023/12 schema
- BMG MARS - initial implementation
- Plate Reader - add plate-reader/REC/2024/06 schema

### Fixed

- All parsers - handle comma as decimal place in float conversion utilities
- Agilent Gen5 - raise AllotropeConversionError on missing Results section
- Agilent Gen5 - add error for multiple read modes
- AppBio QuantStudio - cast data to str before using
- Simplify VI-Cell XR text file reader, removing bug in pivot operation
- Fix edge case where there are multiple measurements for a property in Roche Cedex Bioht

### Changed

- Only return AllotropeConversionError when there is a problem with input data that we expect, add other errors for unexpected problems.
- AppBio Quantstudio Design & Analysis - split structure by experiment type

## [0.1.45] - 2024-08-01

### Changed

- Pandas version updated to 2.2.0 to have calamine engine
- Updated Roche Cedex Bioht adapter to work with the Solution Analyzer ASM schema

## [0.1.44] - 2024-07-30

### Fixed
- Agilent TapeStation Analysis - fix to not include data region documents when there is no region data.
- Agilent TapeStation Analysis - remove `devide identifier` from `device control document`
- Add column normalization to vicell blu reader to fix unrecognized columns due to mismatching characters

## [0.1.43] - 2024-07-22

### Added

- Change Cedex HiRes to recommended release state
- Change Qubit Flex to recommended release state
- Change Qubit 4 ASM to recommended release state
- Change MabTech Apex to recommended release state
- Change Qiacuity to recommended release state

## [0.1.42] - 2024-07-19

### Changed

- Use "calamine" engine for reading excel where possible.
- Relaxed conditions for schema model generator combining classes to handle cases where required key sets created a large number of class versions

## [0.1.41] - 2024-07-18

### Added

- Added Thermo Fisher Qubit Flex adapter
- Added requirement document for Thermo Fisher Qubit Flex adapter
- Added digital PCR and solution analyzer parser requirement templates to /docs

## [0.1.40] - 2024-07-15

### Changed
- AppBio QuantStudio Design & Analysis - redefine stage number as optional

## [0.1.39] - 2024-07-15

### Added

- Added ThermoFisher Qubit4 adapter
- Added requirement doc for ThermoFisher Qubit4 adapter
- Added Roche Cedex HiRes adapter
- Added requirement doc for Roche Cedex HiRes adapter

### Fixed

- Updated the `structure_custom_information_document` function to create dataclasses with default field values set to `None`. This change ensures that custom keys are omitted as they are not required keys.
- Fixed encoding issues while reading units.json file in schemas.py script
- Fixed encoding issues while reading test json files in testing/utils.py script

### Changed
- Updated NON_UNIQUE_IDENTIFIERS to have "group identifier" field

## [0.1.38] - 2024-07-11

### Added

- Added electrophoresis and spectrophotometry parser requirement templates to /docs

### Fixed

- Beckman Vi-cell XR - catch and raise AllotropeConversionError when missing date header
- Make get_model_class_from_schema work with Windows style path
- Agilent Gen5 - support non-numeric emission values for luminescence

### Changed
- AppBio QuantStudio Design & Analysis - allow missing target DNA reference
- Standardize use of "N/A" for strings where a non-applicable value is necessary
- Update `None` filtering to preserve required keys when converting model to dictionary
- Update ASM converter name field to specify the parser name instead of just "allotropy", this is intended to give better granularity on the adapter that did the conversion and not just the library version
- Upgrade pydantic to pull in fix for ForwardRef._evaluate() issue (https://github.com/pydantic/pydantic/issues/9637)
- Agilent Gen5 - update non-numeric emission related values to NaN instead of removing them from ASM


### Deprecated

### Removed

### Security

## [0.1.37] - 2024-06-26

### Added

- Agilent TapeStation Analysis - initial implementation
- Added utility to add both dict and dataclass custom information document to an ASM model

- Added Solution Analyzer BENCHLING/2024/03 schema with the extension of the Data System Document.
### Fixed

- Updated schema cleaner to handle utf-8 characters in unit schema urls
- Updated schema cleaner to handle object schemas with no properties
- Updated Vi-Cell XR requirements doc to reflect support for .txt files
- Handle dashes and slashes in custom information document key names
- Updated Mabtech Apex fields to support LED Filter

### Changed

### Deprecated

### Removed

### Security

## [0.1.36] - 2024-06-24

### Added
- Mabtech Apex - initial implementation
- Added support for parsing Vi-Cell XR txt files
- Electrophoresis - add electrophoresis/BENCHLING/2024/06 schema.
- Added github enforcement that CHANGELOG.md is updated
- Agilent TapeStation Analysis - add test files
- Added requirements for remaining parsers to /docs
- Agilent Gen5 - add Alphalisa assay support
- Add fluorescence point detection measurement extension to Spectrophotometry BENCHLING/2023/12 schema

### Changed

- AppBio Quantstudio - redefine plate well count as optional

## [0.1.35] - 2024-06-07

### Added

- Luminex xPONENT - add ability to parse tabular CSV files

### Fixed

- AppBio QuantStudio Design & Analysis - improved way of infer reference sample and DNA target
- Fix model number and device id in ctl immunospot

### Deprecated
- Roche Cedex Bioht - remove sample role type

## [0.1.34] - 2024-06-04

### Added

- Methodical Mind - initial implementation

### Fixed

- AppBio QuantStudio Design & Analysis - fix missing genotyping determination result
- Revvity Kaleido - remove empty space at beginning of sample identifier

### Changed

- Internal - use modular paths for schema models

## [0.1.33] - 2024-05-29

### Fixed

- Libraries - fix path_util to work outside of allotropy correctly

## [0.1.32] - 2024-05-29

### Added

- Add schema_parser/path_util.py to remove dependency: converter.py -> generate_schemas.py, which pulled script dependencies into allotropy

## [0.1.31] - 2024-05-24

### Added

- Script to create graph visualization of calculated data documents from asm json files
- Details of parser requirements to docs
- Agilent Gen5 - initial implementation
- Add CTL Immunospot adapter

### Fixed

- Fixed missing required field in cell-counting 2023/11 schema
- Fixed missing required field in 2023/09 lum/fluor/abs plate reader schemas

### Changed
- Upgraded allotropy python requirement to python 10
- Updated ASM model class typing to use or union
- AppBio QuantStudio - implement default value for sample role names
- Added kw_only=True for generated schema models

## [0.1.30] - 2024-05-10

### Added

- Global definition of calculated data documents representation
- Bio-Rad Bio-Plex Manager - update to use _get_date_time
- Add structure for Methodical Mind

### Fixed

- AppBio QuantStudio Design & Analysis - remove duplicated ct sd and ct se calculated data documents
- AppBio Quantstudio - Remove duplicated quantity mean calculated data documents from

### Changed

- Update multianalyte model minimum_assay_bead_count to be of type "number" instead of "unitless"
- Bio-Rad Bio-Plex Manager & Luminex xPONENT - update to use multi-analyte-profiling/BENCHLING/2024/01 schema (#394)
- AppBio QuantStudio - remove inner calculated data documents
- AppBio Quantstudio & AppBio QuantStudio Design & Analysis - use global definition of calculated data documents

## [0.1.29] - 2024-04-30

### Added

- Add Vendor display names
- Added liquid-chromatography 2023/09 schema

### Changed

- Improved schema model generation script to handle more complicated schemas

### Removed

- Remove assert in validate_contents



## [0.1.28] - 2024-04-29

### Added

- AppBio QuantStudio Design & Analysis - initial implementation
- Chemometec Nucleoview - add software version field
- Bio-Rad Bio-Plex Manager - initial implementation (#377)
- Internal - add utils for parsing xml (#377)
- Internal - add utility to remove non-required None values from a dataclass
- Beckman PharmSpec - initial implementation

### Fixed

- Beckman Vi-cell Blu - re-add encoding inference
- Unchained Labs Lunatic - corrected concentration unit to conform to unit as reported within the source file
- Luminex xPONENT - corrected to output one multi analyte profiling document per well.
- AppBio Quantstudio - remove duplicated calculated data documents of delta ct se

### Changed

- Agilent Gen5 - use plate-reader/BENCHLING/2023/09 schema

## [0.1.27] - 2024-04-10

### Added

- Added allotropy.testing library, exposing test utils for validating ASM outside of allotropy

### Changed

- Exclude tests from sdist

## [0.1.26] - 2024-04-08

### Fixed

- Beckman Vi-cell Blu - reverted add encoding inference, it is causing unexpected behavior in other environments

## [0.1.25] - 2024-04-05

### Fixed

- Beckman Vi-cell Blu - add encoding inference
- Luminex xPONENT - fix to account for the correct instrument file formatting

## [0.1.24] - 2024-04-03

### Added

- Plate Reader - add optical imaging to plate-reader/BENCHLING/2023/09 schema
- Revvity Kaleido - initial implementation

### Fixed

- Change lightfield with brightfield in transmitted light setting enum of plate reader schema
- Fix missing case for concentration column without A260 prefix in Unchained Labs Lunatic

## [0.1.23] - 2024-03-12

### Added

- Add Qiacuity dPCR adapter

### Changed

- Added ability to specify encoding in top-level functions. Not passing an encoding defaults to UTF-8. To auto-detect encoding with chardet, pass in CHARDET_ENCODING
- Loosen requirement for jsonschema package to increase package compatibility

## [0.1.22] - 2024-03-07

### Fixed

- Fixed Softmax Pro handling of partially filled plates

### Changed

- Moved VendorType to to_allotrope

## [0.1.21] - 2024-03-05

### Fixed

- AppBio QuantStudio - add missing ct mean calculated data documents to relative std curve experiments

### Changed

- Infer size of plate to read all data available in Moldev Softmax

## [0.1.20] - 2024-02-23

### Fixed

- AppBio QuantStudio - remove duplicated delta ct mean calculated data documents
- Fix problem in NanoDrop Eight parser where data source IDs were being used that did not refer to any existing measurement ID

### Changed

- Allow n/a absorbance values in Unchained Labs Lunatic Parser

## [0.1.19] - 2024-02-19

### Fixed

- Fix try_float_or_none bug with evaluating 0 as NaN

## [0.1.18] - 2024-02-19

### Added

- Add try_float_or_nan util and fix bug with evaluating 0 as NaN
- Singleton UUID generator, allowing tests to generate stable ids

### Fixed

- Cast sample identifier to string when saving it in SoftmaxPro parser
- Handle style bug in xlsx files produced by VI-Cell XR instrument

## [0.1.17] - 2024-02-15

### Added

- Automatic validation of generated model in to_allotrope methods with error messages

### Fixed

- Handle invalid values in SoftmaxPro well measurements, filling with "NaN"

## [0.1.16] - 2024-02-08

### Fixed

- Fix mixup of Plate ID and Plate Position in Unchained Labs Lunatic Parser

## [0.1.15] - 2024-02-02

### Added

- pandas_utils module wraps pandas functions to throw AllotropeConversionError

### Fixed

- Total cells column no longer required for vi-cell XR
- Ignore invalid first row when present for vi-cell XR files
- Capture concentration on Nanodrop Eight files that do not have NA Type column
- Removed hardcoding of date parsing around Gen5 plate numbers

### Changed

- Corrections to the spectrophotometry/BENCHLING/2023/12 schema to account for feedback from Allotrope Modeling Working Group
- Replace null with N/A in Moldev Softmax Pro

## [0.1.14] - 2024-01-31

### Added

- Luminex xPONENT - initial implementation

### Fixed

- Ignore calculated data documents entry in output of Moldev Softmax Pro when there are no calculated data documents
- Check for raw data indicator in plate header for Moldev Softmax Pro

## [0.1.13] - 2024-01-19

### Added

- Add parser for ChemoMetic NucleoView
- Add parser for Nanodrop Eight
- Add calculated data documents to Unchained Labs Lunatic adapter
- Add calculated data documents to Moldev Softmax Pro
- Add multi-analyte-profiling BENCHLING/2024/01 schema
- Add non-numeric options for tQuantityValue value property
- Add support for non-numeric values to ChemoMetic NucleoView
- Add context manager to handle backups to schema generation script
- Add --regex argument to schema generation script

### Fixed

- Perkin Elmer Envision: calculated data name now captures string to the left - rather than right - of the ‘=’ in the Formula cell

### Changed

- Simplify Moldev Softmax Pro parsing with dataclasses
- Update plate reader schema in Moldev Softmax Pro
- Standardized on UNITLESS constant ("(unitless)") for unitless values. Changed Perkin Elmer Envision, which formerly used "unitless"
- Increase test coverage of calculated data documents on Perkin Elmer Envision

## [0.1.12] - 2023-12-12

### Added

- Calculated data documents to PerkinElmer EnVision
- Add Unchained Labs Lunatic adapter

### Fixed

- AppBio QuantStudio - fix per-well calculated documents

### Changed

- AppBio QuantStudio - refactor builders as create methods

## [0.1.11] - 2023-12-04

### Added

- Documentation - add parser structure documentation (#108)

### Changed

- Agilent Gen5 - refactor to use explicit dataclasses structure
- Beckman Vi-cell Blu - update to use cell-counting/BENCHLING/2023/11 schema
- Beckman Vi-cell XR - update to use the cell-counting/BENCHLING/2023/11 schema
- PerkinElmer EnVision - update use the plate-reader/BENCHLING/2023/09 schema
- All parsers - standardize and clarify exception messages

## [0.1.10] - 2023-11-14

### Added

- Add data system document to plate reader schema

### Changed

- AppBio QuantStudio - redefine reporter dye setting for genotyping experiments (#102)
- All parsers - update TimeStampParser.parse() to raise for invalid input

## [0.1.9] - 2023-11-03

### Added

- AppBio QuantStudio - add missing example outputs for tests
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

- AppBio QuantStudio - test for broken calculated document structure

### Fixed

- AppBio QuantStudio - fix bug in result caching

### Changed

- AppBio QuantStudio - allow block type to have plate well count in any position
- Replace datetime.timezone with ZoneInfo in TimestampParser
- Implement CsvReader as child of LinesReader

## [0.1.5] - 2023-10-04

### Added

- Parser for AppBio Absolute Q dPCR exports

### Fixed

- AppBio QuantStudio - redefine calculated data documents references as required
- Update dPCR schema "experiment type" enum to have correct values

### Changed

- dPCR - make "fluorescence intensity threshold setting" optional in the dPCR schema
- Internal - update the "calculated datum" property on the calculated data documents to allow different units

## [0.1.4] - 2023-10-03

### Fixed

- AppBio QuantStudio - remove duplication of calculated documents related to quantity measurements
- qPCR - rename "qPCR detection chemistry" to "PRC detection chemistry" in PCR schemas
- dPCR - add missing @dataclass annotation to TQuantityValueNumberPerMicroliter

## [0.1.3] - 2023-10-03

### Fixed

- AppBio QuantStudio - redefine the way calculated documents are structured for relative standard curve
- dPCR - fixed some issues in dPCR schema and corresponding model updates
- AppBio QuantStudio - accept comma as thousand indicator in all sections

## [0.1.2] - 2023-09-27

### Added

- dPCR - add Digital PCR (dPCR) documents
- AppBio QuantStudio - add calculated documents
- AppBio QuantStudio - add genotyping data structure test

### Fixed

- AppBio Quantstudio - remove typing ignore tags from the construction of structure
- AppBio Quantstudio - ignore unexpected sections in input file
- AppBio Quantstudio - accept comma as thousand indicator in results section

## [0.1.1] - 2023-09-22

### Changed

- Internal - loosened requirement for jsonschema package to make allotropy compatible with datamodel-code-generator

## [0.1.0] - 2023-09-18

### Added

- Initial commit, includes support for:
  - Agilent Gen5
  - AppBio QuantStudio
  - Beckman Vi-Cell BLU
  - Beckman Vi-Cell XR
  - MolDev SoftMax Pro
  - NovaBio Flex2
  - PerkinElmer Envision
  - Roche Cedex BioHT
