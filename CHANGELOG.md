# Changelog

All notable changes to this packages will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.92] - 2025-06-02

### Added

- Revvity Matrix - Support headers data (#1003)
- Agilent Gen5 - Add support for spectral data (#999)

## [0.1.91] - 2025-05-22

### Fixed

- Molecular Devices SoftMax Pro - handle case where group data is missing value for all rows (#1000)

## [0.1.90] - 2025-05-21

### Added

- Unchained Labs Lunatic - add unread data (#984)
- Plate Reader - Add schema mapper for schema 2025/03 (#989)
- Molecular Devices SoftMax Pro - update logic on group data to get calculated entries and custom information (#992)

## [0.1.89] - 2025-05-20

## [0.1.88] - 2025-05-14

### Added

- Appbio Absolute Q - add unread data (#958)
- Benchling Empower - add custom fields (#975)
- Molecular Devices SoftMax Pro - add calculated data from group summaries (#977)
- Unchained Labs Lunatic - use calcdocs library (#978)
- Tecan Magellan - check for well positions column in reader (#983)
- Molecular Devices SoftMax Pro - add infinite values in group data to error document (#987)
- Agilent Gen5 - add support for fluorescence polarization (#976)

### Fixed

- Beckman Echo Plate Reformat - update measurement time to fill missing date with file date if needed (#990)
- Beckman Echo Plate Reformat -  remove accidental volume conversion of survey volume results (#982)
- Global - make extension check case insensitive  (#985)
- MSD Methodical Mind - change regex too permissive for data section in reader (#981)

## [0.1.89] - 2025-05-20

## [0.1.87] - 2025-05-02

### Added

- Molecular Devices SoftMax Pro - add check for duplicated plate block names (#979)

## [0.1.89] - 2025-05-20

## [0.1.86] - 2025-04-17

### Added

- Molecular Devices SoftMax Pro - add group identifier to wells from group blocks (#956)
- Cytiva Unicorn - add logic to parse Logbook  (#963)
- BD Biosciences FACSDiva - initial implementation (#954)

### Fixed

- Cytiva Unicorn - fix units of chromatograms to be retention volume instead of retention time (#972)

### Changed

- FlowJo - Add strategy pattern for getting region vertices (#957)

## [0.1.89] - 2025-05-20

## [0.1.85] - 2025-04-16

### Added

- Internal - add ability to handle nested lists in JSON to CSV library (#966)
- Cytiva Biacore T200 Control - fix missing stream data errors (#955)

### Changed

- Spectrophotometry - Standardize calculated data definition (#961)

## [0.1.89] - 2025-05-20

## [0.1.84] - 2025-04-15

### Added

- Molecular Devices SoftMax Pro -  remove enforcement of WellPlateName in group data for single plate experiments (#960)

### Fixed

- Perkin Elmer Envision - update filter bandwidth regex and optional plate maps (#964)

## [0.1.89] - 2025-05-20

## [0.1.83] - 2025-04-10

### Added

- AppBio Absolute Q - add support for zip files (#953)
- Molecular Devices SoftMax Pro - Use date last saved as measurement time  (#946)

### Fixed

- Benchling Empower - store result fields separately and ignore missing/group type peaks (#959)
- Internal - improve error messaging for errors in various parsers (#952)
- AppBio AbsoluteQ - allow single dye setting in summary file (#947)

### Changed

- Perkin Elmer Envision - use Calcdocs library (#945)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.81] - 2025-04-02

### Added

- Beckman Echo Plate Reformat - add unread keys and mark as REC (#944)
- FlowJo - add support for Ellipsoid/CurlyQuad gates and Statistics documents (#939)
- Beckman Echo Plate Reformat - initial implementation (#825)
- Appbio Quantstudio design and analysis - store quantity as custom info when calcdata ignores value (#941)
- Appbio Quantstudio design and analysis - redefine cycle threshold result as required data source (#934)
- MSD Discovery Workbench - get unread data (#936)
- Flowjo - initial implementation (#930)
- Agilent OpenLab CDS - initial implementation (#864)
- NovaBio Flex2 - add parsing for unit row (#932)

### Fixed

- Global - handle cases where encoding detection detects the wrong encoding (#940)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.80] - 2025-03-19

### Added

- Cytiva Biacore T200 Control - Update release status to recommended (#933)
- Cytiva Biacore T200 Control: add calculated data (#931)
- MSD Methodical Mind - handle export formats with missing spots and spot legend (#909)
- AppBio QuantStudio Design & Analysis - implement RT-PCR parsing (#928)
- MSD Methodical Mind - handle oddly parsed whitespace characters in header with more robust header parsing (#929)
- AppBio QuantStudio RT-PCR - improve logic handling splitting header and data in reader (#921)

### Changed

- BMG Labtech SMART Control - migrate calc data docs to use lib (#927)
- MSD Discovery Workbench - migrate to calculated data lib (#919)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.79] - 2025-03-11

### Fixed

- ChemoMetec Nucleoview - add validation for cell viability field. (#918)

### Changed

- Benchling Thermo Fisher Scientific Chromeleon - update DeviceDocument to follow schema mapper pattern (#920)
- AppBio QuantStudio RT-PCR - use calcdocs library (#917)
- AppBio QuantStudio Design & Analysis - use calcdocs library (#883)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.78] - 2025-03-04

### Fixed

- Mabtech Apex - fix typo that prevents getting analyst field (#913)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.77] - 2025-03-04

### Added

- BMG Labtech SMART Control - add unread data to ASM (#881)
- Thermo Fisher Scientific Chromeleon - initial implementation (#894)
- Roche Cedex HiRes - add unread data to ASM (#872)
- ChemoMetec Nucleoview - Add unread data to ASM. (#857)
- MSD Methodical Mind - add unread data to ASM (#873)
- Cytiva Biacore T200 Control - Add sensorgram and report point data to the ASM  (#899)
- Benchling Waters Empower Adapter - add peak analyte amount and relative peak analyte amount (#898)

### Fixed

- MSD Methodical Mind - add type verification for luminescence (#900)
- Benchling Empower - use SampleName for sample identifier (#897)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.76] - 2025-02-19

### Added

- Liquid Chromatography - move fraction events to measurement aggregate document (#893)
- Liquid Chromatography - add new fields to the BENCHLING/2023/09 schema (#891)
- Thermo Fisher Scientific SkanIt - add support for Luminescence measurement type (#887)
- Cytiva Unicorn - add fraction events (#892)

### Fixed

- ChemoMetec Nucleoview - handle file with commas at the end of the line (#889)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.75] - 2025-02-11

### Added

- Cytiva Unicorn - add void volume and flow rate (#880)
- Bio-Rad CFX Maestro - update release state to recommended (#879)
- AppBio QuantStudio Design & Analysis - add back reference fields as custom data processing info (#878)
- Internal - improve calcdoc library implementation (#874)
- Agilent Gen5 - Add unread data to ASM (#870)
- Bio-Rad CFX Maestro - Add unread data to ASM (#850)
- Luminex xPONENT - add descriptive error for Minimum bead count setting (#865)

### Fixed

- Plate Reader REC 2024/06 - add custom data to fluorescence measurement type (#886)
- Luminex xPONENT - map settings from different source, add error document for Nan values (#868)
- Agilent TapeStation Analysis - add missing calculated data from RNA tag (#866)
- Luminex xPONENT - do not throw an error if an optional value is missing in the input file (#867)
- Unchained Labs Lunatic - handle different cases for column headers (#863)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.74] - 2025-01-28

### Added

- AppBio QuantStudio RT-PCR - add back reference fields as custom data processing info (#860)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.73] - 2025-01-28

### Added

- Internal - add initial json-to-csv library (#767)
- Thermo Fisher Qubit Flex - Add unread data to asm (#855)
- Internal - implement special views for Quantstudio design analysis in calcdoc (#858)
- Internal - implement calculated data documents library (#838)
- Bio-Rad CFX Maestro - Use qpcr rec/2024/09 schema mapper (#837)
- AppBio QuantStudio Design & Analysis - Use qpcr rec/2024/09 schema mapper (#836)
- Thermo fisher Nanodrop One - Add unread data to customer information document (#852)
- AppBio QuantStudio RT-PCR - Use qpcr rec/2024/09 schema mapper (#856)
- Thermo Fisher Qubit4 - Add unread data to asm. (#854)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.72] - 2025-01-21

### Added

- BMG Labtech SMART Control - initial implementation (#831)
- Cytiva Unicorn - add start time to device control doc (#851)
- Cytiva Unicorn - add peaks (#849)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.71] - 2025-01-14

### Added

- Internal: add missing package dependencies

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.70] - 2025-01-14

### Added

- Beckman coulter biomek - add support for .log files (#840)
- Unchained Labs Lunatic - Added concentration factor as data processing field in asm (#844)
- Cytiva Unicorn - Update inner column diameter and analyst fields (#842)
- Cytiva Unicorn - handle missing sample id and injection volume (#841)
- Beckman Coulter Adapters - Standardize display name (#834)
- MSD Workbench - add .txt file support (#835)
- Revert - "feat:  AppBio QuantStudio RT-PCR - Use qpcr rec/2024/09 schema mapper" (#839)
- Cytiva Unicorn - improve handling of optional values  (#829)
- Cytiva Biacore T200 Control - initial implementation (#765)
-  AppBio QuantStudio RT-PCR - Use qpcr rec/2024/09 schema mapper (#833)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.69] - 2024-12-16

### Added

- Molecular Devices SoftMax Pro - add support for spectrum data (#819)
- ChemoMetec NucleoView - Incorporate error document when viable cell density is missing (#822)
- Cytiva Unicorn - allow optional values (#823)
- Plate Reader - add custom data cube to BENCHLING/2023/09 schema (#815)
- CTL ImmunoSpot - support v7.0.38 software version export format (#809)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.68] - 2024-12-12

### Added

- Benchling Waters Empower Adapter, Cytiva Unicorn, Thermo Fisher Scientific Genesys On-Board, Beckman Coulter Biomek - mark parsers as RECOMMENDED (#820)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.67] - 2024-12-11

### Added

- Liquid Handler - add injection volume setting, and add error documents to schema mapper (#814)
- Benchling Waters Empower Adapter - initial implementation (#779)
- Cell Counting - migrate adapters to the cell-counting/REC/2024/09 schema (#813)
- Beckman Vi-Cell XR - update to use cell-counting/REC/2024/09 schema (#807)
- Unchained Labs Lunatic - update adapter to map to Plate Reader REC/2024/06 schema (#806)
- Cytiva Unicorn - initial implementation (#796)

### Fixed

- Meso Scale Discovery Workbench - Fix missing calculated data for some measurements (#812)
- PerkinElmer Envision, Thermo Fisher Scientific NanoDrop Eight/8000, Unchained Labs Lunatic - fix a couple cases where we don't cast to str before accessing (#808)
- Global - update schemas to align the use of `μ` characters with allotrope (#805)

### Changed

- Liquid Chromatography - Added fluorescence-cube-detector measurementDocumentItems to liquid-chromatography measurement schemas (#811)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.66] - 2024-12-05

### Added

- Beckman Coulter Biomek - initial implementation (#799)
- MSD Discovery Workbench - initial implementation (#786)
- Tecan Magellan - initial implementation (#798)
- Mabtech Apex - capture unread keys in custom information document (#764)
- MSD Methodical Mind - add multiple spots recorded for the same well within the same measurement agg document. (#794)
- Thermo Fisher Scientific Genesys On-Board - initial implementation (#792)

### Fixed

- MSD Methodical Mind - correct location ID handling (#800)
- Liquid Chromatography - nest all device control document definitions under aggregate document in schema (#801)
- MSD Methodical Mind - handle case were there are empty identifiers, and handle digital signature at the top of the file (#795)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.65] - 2024-11-23

### Added

- AppBio AbsoluteQ - add support for summary file format (#790)
- AppBio AbsoluteQ - add support for fluorescence data cube format (#785)
- Thermo Fisher Scientific VISIONlite - extend support for Genesys150 file  (#788)
- AppBio AbsoluteQ  - support multichannel file type (#787)
- AppBio QuantStudio RT-PCR - support xlsx format (#782)
- Liquid-Handler - initial version of schema (#771)
- Thermo Fisher Scientific VISIONlite - support new file format and calculated data (#774)

### Fixed

- Molecular Devices SoftMax Pro - forward-fill columns in group summaries correctly (#784)
- Molecular Devices Softmax Pro - add check for expected rows in plate data table (#776)
- Qiacuity DPCR - add encoding detection/artifacts and handle different column names for concentration (#775)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.64] - 2024-11-13

### Added

- AppBio QuantStudio RT-PCR - handle format where only Results section is provided (#770)
- Beckman PharmSpec - update adapter to use Solution Analyzer schema REC/2024/09 (#749)
- Agilent Gen5 - Support results not grouped in a single table  (#768)
- Internal - add function to SeriesData to get unread keys (#766)
- Unchained Labs Lunatic - add ability to parse spectrum measurements (#762)

### Fixed

- Thermo Fisher Scientific NanoDrop Eight - support headers ending with trailing whitespace (#772)

### Changed

- Binding Affinity Analyzer - sensor chip document hierarchy level change (#752)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.63] - 2024-11-01

### Added

- Thermo Fisher Scientific VISIONlite - initial implementation (#759)
- AppBio QuantStudio Design & Analysis - update primary analysis experiment type (#753)
- Roche Cedex BioHT - update adapter to use Solution Analyzer schema REC/2024/09 (#741)
- BMG MARS - Added support for Luminescence readout for BMG Mars parser (#748)

### Fixed

- Agilent Gen5 Image - include transmission light setting when it is inside the channel setting (#745)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.62] - 2024-10-30

### Added

- Global - include unc path in all existing adapters (#721)
- Binding Affinity Analyzer - initial version of schema (#740)
- Novabio Flex2 - Update Adapter to use Solution Analyzer schema REC/2024/09 (#743)
- Bio-Rad CFX Maestro - initial implementation (#744)
- Internal - add the ability to handle lists of dataclasses in json structuring library (#716)
- Molecular Devices SoftMax Pro - report non numeric values in error document #713 (#739)

### Fixed

- Thermo Fisher Scientific NanoDrop Eight - handle alternative column names (#731)
- Revvity Kaleido - update v3/3.5 parser to handle a pure CSV export file where empty lines are populated with commas (#742)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.61] - 2024-10-16

### Added

- AppBio QuantStudio Design & Analysis - add xls support and additional filter check for empty stage number column (#724)

### Removed

- Molecular Devices SoftMax Pro - report non numeric values in error document (#725)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.60] - 2024-10-15

### Added

- Agilent Tapestation Analysis - update parser to use electrophoresis/BENCHLING/2024/09 (#715)
- Electrophoresis - add electrophoresis/BENCHLING/2024/09 schema and schema mapper (#715)
- Solution Analyzer - add solution-analyzer/rec/2024/09 schema mapper (#714)
- Molecular Devices SoftMax Pro - report non numeric values in error document (#713)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.59] - 2024-10-11

### Added

- Thermo Fisher Scientific SkanIt & Revvity Matrix - update adapters release statuses to RECOMMENDED (#719)

### Fixed

- AppBio QuantStudio RT-PCR - remove omitted wells from calculated data document data sources (#717)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.58] - 2024-10-09

### Fixed

- Thermo Fisher Scientific Qubit Flex - add fields that were accidentally removed/renamed in refactor (#711)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.57] - 2024-10-09

### Added

- Revvity Kaleido - add v3.5 to supported software versions (#707)
- Solution Analyzer - add solution-analyzer/REC/2024/09 (#706)
- AppBio QuantStudio RT-PCR - support skipping wells that have no results in the raw data file, indicating an omitted well (#689)
- AppBio QuantStudio RT-PCR - add "quantity" calculated data documents for non-STANDARD wells (#698)
- Plate Reader - update adapters using plate-reader/2024/06 schema to include ASM file identifier (#695)
- Thermo Fisher Scientific NanoDrop 8000 & Thermo Fisher Scientific NanoDrop Eight - support alternative reporting format for absorbance measurements (#688)
- Agilent Gen5 - add support for error documents in the  (#694)
- Electrophoresis - add the electrophoresis/REC/2024/06 schema (#693)
- MSD Methodical Mind - update to use plate-reader/REC/2024/06 schema (#692)
- Agilent Gen5 Image - add support for no result sections file examples (#679)
- Thermo Fisher Scientific SkanIt - initial implementation (#658)
- Perkin Elmer Envision - update to use plate-reader/REC/2024/06 schema (#686)
- BMG Mars - update to use plate-reader/REC/2024/06 schema (#685)
- Spectrophotometry - add spectrophotometry/REC/2024/06 schema (#684)
- Thermo Fisher Scientific Nanodrop Eight - initial implementation (#683)
- Unchained Labs Lunatic - add additional metadata from header block (#680)

### Fixed

- Molecular Devices SoftMax Pro - raise error for unsupported Group data format (#696)
- Agilent Gen5 - raise error when there are calculated data but no measurements in results (#691)
- Beckman Vi-Cell BLU - filter NaN values when reading cell counts (#687)
- Global - update DataSeries to use float parsing utility when reading a float value, in order to better handle edge cases (#682)

### Changed

- Thermo Fisher Scientific Qubit Flex - refactor parser to use schema mapper design pattern (#699)
- Global - change the way custom information is organized in schema mappers and ASM outputs to be consistent with future expectations of ASM (#673)
- Thermo Fisher Scientific NanoDrop 8000 & Nanodrop Eight - rebrand NanoDrop Eight parser to NanoDrop 8000 (#652)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.56] - 2024-09-26

### Added

- AppBio Quantstuido Design & Analysis - add Amp score and Cq confidence calculated data documents (#670)
- Molecular Devices SoftMax Pro - add support for kinetic measurements files (#674)
- Revvity Matrix - initial implementation (#656)

### Fixed

- AppBio Quantstuido Design & Analysis - fix Y-intercept and Slope references as data sources for quantity calculated data document (#670)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.55] - 2024-09-26

### Added

- AppBio Quantstuido - add cache decorator to amp score calculated data construction (#666)
- ChemoMetec NC View - initial implementation (#665)

### Fixed

- qPRC & AppBio QuantStudio Design & Analysis - make "PCR Detection Chemistry" optional and omit when missing instead of using N/A (#668)
- Perkin Elmer Envision - remove leading '0' from well identifier numbers (#671)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.54] - 2024-09-23

### Added

- AppBio Quantstuido - add additional metadata fields (#661)

### Fixed

- Unchained Labs Lunatic - handle missing 'Sample name' and missing 'Table' label before table parser (#660)
- Agilent Gen5 - cast measurement label to string, since it can numeric when reading directly from dataframe (e.g. a single wavelength) (#657)

### Changed

- Appbio QuantStudio Design & Analysis - simplify sheets needed to infer presence/absence experiment type inference (#659)
- Appbio QuantStudio Design & Analysis - allow software name and version to be None (#659)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.53] - 2024-09-17

### Added

- AppBio QuantStudio RT-PCR - add Amp score and Cq conf calculated documents (#670)
- AppBio QuantStudio RT-PCR - add custom information to processed data document (#645)
- Plate Reader - add schema mapper for plate-reader/REC/2024/06 schema (#642)
- AppBio QuantStudio RT-PCR - add checks for missing well item amplification and results data in quantstudio (#643)
- Thermo Fisher Scientific Nanodrop One - add support for CSV files (#649)
- Thermo Fisher Scientific SkanIt - initial implementation (#658)
- Agilent Gen5 - add support for label format "[excitation wavelength], [emission wavelength]" for fluorescence point detection (#650)

### Fixed

- AppBio QuantStudio RT-PCR - fix bad reference for y-intercept and slope in quantity calculated data document (#670)
- Molecular Devices SoftMax Pro - correctly format timezone (#642)

### Changed

- Molecular Devices SoftMax Pro - refactor to use the schema mapper (#642)
- Agilent Gen5 - update to use plate-reader/REC/2024/06 schema (#633)
- Thermo Fisher Scientific Genesys30 - update release state to RECOMMENDED (#654)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.52] - 2024-09-12

### Fixed

- Roche Cedex Bioht, Thermo Fisher Scientific Qubit 4 & Flex - fix bug where name of contents instead of contents was being passed to reader (#648)

### Changed

- Global - use dateutil timezone instead of pytz, because pytz can create incorrect timezones when not localized (#644)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.51] - 2024-09-09

### Added

- Molecular Devices SoftMax Pro - add error message for zero plate reader documents (#635)
- AppBio QuantStudio RT-PCR - update data sources for quantity calculated documents with y-intercept and Slope (#630)

### Fixed

- Global - allow try_int to handle decimal point in int values (e.g. 1.0) (#638)

### Changed

- Molecular Devices SoftMax Pro - update to plate-reader/REC/2024/06 schema (#627)
- Molecular Devices SoftMax Pro - remove `NaN` measurements to comply with the new `REC` schema (#627)
- Unchained Labs Lunatic - change reader so that it supports both formats (with/without header) for both file types (#631)
- Molecular Devices SoftMax Pro - disregard compartment temperature when is reported as 0 (#635)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.50] - 2024-08-30

### Added

- Global - add `supported_extensions` to Vendor, allowing parsers to specify supported file extensions (#617)
- Agilent Gen5 - add support for multiple read modes (#624)
- Thermo Fisher Scientific Nanodrop One - initial implementation

### Fixed

- Mabtech Apex - update regex to handle scenarios where first word in the machine ID section has all letter uppercase

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.49] - 2024-08-21

### Added

- AppBio QuantStudio Design & Analysis - add primary analysis experiment type
- Thermo Fisher Scientific Genesys30 - initial implementation
- Unchained Lunatic - add support for xlsx exports in
- Global - add column special character normalization to pandas util

### Fixed

- Molecular Devices SoftMax Pro - fix case where some columns were incorrectly identified as not numeric for calculated data documents. Added exceptions for Masked and Range values which will be treated as NaN.

### Changed

- Spectrophotometry - updated the schema mapper to accommodate absorbance spectrum data cubes

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.48] - 2024-08-15

### Changed

- BMG MARS - updated release state to RECOMMENDED
- Roche NovaBio Flex2 - update to use solution-analyzer/REC/2024/03 schema

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.47] - 2024-08-13

### Fixed

- Roche Cedex Bioht - fix mis-reporting some analyte units

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.46] - 2024-08-13

### Added

- Bio-Rad Bio-Plex Manager - add plate id field
- Spectrophotometry - add luminescence point detection, absorption spectrum detection, fluorescence emission detection measurement extension to spectrophotometry/BENCHLING/2023/12 schema
- BMG MARS - initial implementation
- Plate Reader - add plate-reader/REC/2024/06 schema

### Fixed

- Global - handle comma as decimal place in float conversion utilities
- Agilent Gen5 - raise AllotropeConversionError on missing Results section
- Agilent Gen5 - add error for multiple read modes
- AppBio QuantStudio RT-PCR - cast data to str before using
- Beckman VI-Cell XR - simplify text file reader, removing bug in pivot operation
- Roche Cedex Bioht - fix edge case where there are multiple measurements for a property in

### Changed

- Global - only return AllotropeConversionError when there is an anticipated error with input data, add other errors for unexpected problems
- AppBio Quantstudio Design & Analysis - split structure by experiment type

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.45] - 2024-08-01

### Changed

- Internal - pandas version updated to 2.2.0 to have calamine engine
- Roche Cedex Bioht - to use solution-analyzer/rec/2024/09 schema

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.44] - 2024-07-30

### Fixed
- Agilent TapeStation Analysis - fix to not include data region documents when there is no region data.
- Agilent TapeStation Analysis - remove `devide identifier` from `device control document`
- Add column normalization to vicell blu reader to fix unrecognized columns due to mismatching characters

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.43] - 2024-07-22

### Added

- Roche Cedex HiRes - update release status to RECOMMENDED
- Thermo Fisher Scientific Qubit Flex - update release status to RECOMMENDED
- Thermo Fisher Scientific Qubit 4 - update release status to RECOMMENDED
- MabTech Apex - update release status to RECOMMENDED
- Qiacuity dPCR - update release status to RECOMMENDED

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.42] - 2024-07-19

### Changed

- Internal - use "calamine" engine for reading excel where possible.
- Internal - relaxed conditions for schema model generator combining classes to handle cases where required key sets created a large number of class versions

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.41] - 2024-07-18

### Added

- Thermo Fisher Scientific Qubit 4 - initial implementation
- Documentation - add dPCR and solution analyzer parser requirement templates

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.40] - 2024-07-15

### Changed

- AppBio QuantStudio Design & Analysis - redefine stage number as optional

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.39] - 2024-07-15

### Added

- Thermo Fisher Scientific Qubit 4 - initial implementation
- Roche Cedex HiRes - initial implementation

### Fixed

- Internal - update the `structure_custom_information_document` function to create dataclasses with default field values set to `None`. This change ensures that custom keys are omitted as they are not required keys.
- Internal - fix encoding issues while reading units.json file in schemas.py script
- Internal - fix encoding issues while reading test json files in testing/utils.py script

### Changed

- Internal - update NON_UNIQUE_IDENTIFIERS to have "group identifier" field

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.38] - 2024-07-11

### Added

- Documentation - add electrophoresis and spectrophotometry parser requirement templates

### Fixed

- Beckman Vi-Cell XR - catch and raise AllotropeConversionError when missing date header
- Internal - fix get_model_class_from_schema work with Windows style path
- Agilent Gen5 - support non-numeric emission values for luminescence

### Changed

- AppBio QuantStudio Design & Analysis - allow missing target DNA reference
- Global - standardize use of "N/A" for strings where a non-applicable value is necessary
- Global - update `None` filtering to preserve required keys when converting model to dictionary
- Global - update ASM converter name field to specify the parser name instead of just "allotropy", this is intended to give better granularity on the adapter that did the conversion and not just the library version
- Internal - upgrade pydantic to pull in fix for ForwardRef._evaluate() issue (https://github.com/pydantic/pydantic/issues/9637)
- Agilent Gen5 - update non-numeric emission related values to NaN instead of removing them from ASM

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.37] - 2024-06-26

### Added

- Agilent TapeStation Analysis - initial implementation
- Internal - add utility to add both dict and dataclass custom information document to an ASM model

- Added Solution Analyzer BENCHLING/2024/03 schema with the extension of the Data System Document.
### Fixed

- Internal - updated schema cleaner to handle utf-8 characters in unit schema urls
- Internal - updated schema cleaner to handle object schemas with no properties
- Documentation - updated Beckman Vi-Cell XR requirements doc to reflect support for .txt files
- Global - handle dashes and slashes in custom information document key names
- Mabtech Apex - updated fields to support LED Filter

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.36] - 2024-06-24

### Added
- Mabtech Apex - initial implementation
- Beckman Vi-Cell XR - add support for parsing txt files
- Electrophoresis - add electrophoresis/BENCHLING/2024/06 schema
- Agilent TapeStation Analysis - add test files
- Documentation - add requirements for remaining parsers to /docs
- Agilent Gen5 - add Alphalisa assay support
- Spectrophotometry - add fluorescence point detection measurement extension to spectrophotometry/BENCHLING/2023/12 schema

### Changed

- AppBio QuantStudio RT-PCR - redefine plate well count as optional

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.35] - 2024-06-07

### Added

- Luminex xPONENT - add ability to parse tabular CSV files

### Fixed

- AppBio QuantStudio Design & Analysis - improved way of infer reference sample and DNA target
- CTL ImmunoSpot - fix model number and device id

### Deprecated
- Roche Cedex Bioht - remove sample role type

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.34] - 2024-06-04

### Added

- MSD Methodical Mind - initial implementation

### Fixed

- AppBio QuantStudio Design & Analysis - fix missing genotyping determination result
- Revvity Kaleido - remove empty space at beginning of sample identifier

### Changed

- Internal - use modular paths for schema models

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.33] - 2024-05-29

### Fixed

- Internal - fix path_util to work outside of allotropy correctly

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.32] - 2024-05-29

### Added

- Internal - add schema_parser/path_util.py to remove dependency: converter.py -> generate_schemas.py, which pulled script dependencies into allotropy

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.31] - 2024-05-24

### Added

- Internal - add script to create graph visualization of calculated data documents from asm json files
- Agilent Gen5 - initial implementation
- CTL ImmunoSpot - initial implementation

### Fixed

- Cell Counting - fix missing required field in cell-counting/BENCHLING/2023/11 schema
- Plate Reader - fix missing required field in plate-reader/BENCHLING/2023/09 schema

### Changed
- Internal - upgraded allotropy python requirement to python 10
- Internal - updated ASM model class typing to use | union
- AppBio QuantStudio RT-PCR - implement default value for sample role names
- Internal - add kw_only=True for generated schema models

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.30] - 2024-05-10

### Added

- Global - add definition of calculated data documents representation
- Bio-Rad Bio-Plex Manager - update to use _get_date_time
- MSD Methodical Mind - refactor to use structure pattern

### Fixed

- AppBio QuantStudio Design & Analysis - remove duplicated ct sd and ct se calculated data documents
- AppBio QuantStudio RT-PCR - Remove duplicated quantity mean calculated data documents from

### Changed

- Multi Analyte Profiling - update minimum_assay_bead_count to be of type "number" instead of "unitless"
- Bio-Rad Bio-Plex Manager & Luminex xPONENT - update to use multi-analyte-profiling/BENCHLING/2024/01 schema (#394)
- AppBio QuantStudio RT-PCR - remove inner calculated data documents
- AppBio Quantstudio & AppBio QuantStudio Design & Analysis - use global definition of calculated data documents

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.29] - 2024-04-30

### Added

- Global - add Vendor display names
- Liquid Chromatography - add liquid-chromatography/REC/2023/09 schema

### Changed

- Internal - improve schema model generation script to handle more complicated schemas

### Removed

- Internal - remove assert in validate_contents

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.28] - 2024-04-29

### Added

- AppBio QuantStudio Design & Analysis - initial implementation
- ChemoMetec Nucleoview - add software version field
- Bio-Rad Bio-Plex Manager - initial implementation (#377)
- Internal - add utils for parsing xml (#377)
- Internal - add utility to remove non-required None values from a dataclass
- Beckman PharmSpec - initial implementation

### Fixed

- Beckman Vi-Cell BLU - re-add encoding inference
- Unchained Labs Lunatic - corrected concentration unit to conform to unit as reported within the source file
- Luminex xPONENT - corrected to output one multi analyte profiling document per well.
- AppBio QuantStudio RT-PCR - remove duplicated calculated data documents of delta ct se

### Changed

- Agilent Gen5 - use plate-reader/BENCHLING/2023/09 schema

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.27] - 2024-04-10

### Added

- Internal - add allotropy.testing library, exposing test utils for validating ASM outside of allotropy

### Changed

- Internal - exclude tests from sdist

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.26] - 2024-04-08

### Fixed

- Beckman Vi-Cell BLU - reverted add encoding inference, it is causing unexpected behavior in other environments

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.25] - 2024-04-05

### Fixed

- Beckman Vi-Cell BLU - add encoding inference
- Luminex xPONENT - fix to account for the correct instrument file formatting

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.24] - 2024-04-03

### Added

- Plate Reader - add optical imaging to support to plate-reader/BENCHLING/2023/09
- Revvity Kaleido - initial implementation

### Fixed

- Plate Reader - change lightfield with brightfield in transmitted light setting enum in plate-reader/BENCHLING/2023/09
- Unchained Labs Lunatic - fix missing case for concentration column without A260 prefix

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.23] - 2024-03-12

### Added

- Qiacuity dPCR - initial implementation

### Changed

- Global - add ability to specify encoding in top-level functions. Not passing an encoding defaults to UTF-8. To auto-detect encoding with chardet, pass in CHARDET_ENCODING
- Internal - loosen requirement for jsonschema package to increase package compatibility

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.22] - 2024-03-07

### Fixed

- Molecular Devices Softmax Pro - fix handling of partially filled plates

### Changed

- Internal - moved VendorType to to_allotrope

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.21] - 2024-03-05

### Fixed

- AppBio QuantStudio RT-PCR - add missing ct mean calculated data documents to relative std curve experiments

### Changed

- Molecular Devices Softmax Pro - infer size of plate to read all data available

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.20] - 2024-02-23

### Fixed

- AppBio QuantStudio RT-PCR - remove duplicated delta ct mean calculated data documents
- Thermo Fisher Scientific NanoDrop Eight - fix problem where data source IDs were being used that did not refer to any existing measurement ID

### Changed

- Unchained Labs Lunatic - allow n/a absorbance values

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.19] - 2024-02-19

### Fixed

- Global - fix try_float_or_none bug with evaluating 0 as NaN

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.18] - 2024-02-19

### Added

- Global - add try_float_or_nan util and fix bug with evaluating 0 as NaN
- Internal - add singleton UUID generator, allowing tests to generate stable ids

### Fixed

- Molecular Devices Softmax Pro - cast sample identifier to string
- Beckman Vi-Cell XR - handle style bug in xlsx files produced by VI-Cell XR instrument

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.17] - 2024-02-15

### Added

- Global - add automatic validation of generated model in to_allotrope methods with error messages

### Fixed

- Molecular Devices Softmax Pro - handle invalid values in well measurements, filling with "NaN"

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.16] - 2024-02-08

### Fixed

- Unchained Labs Lunatic - fix mixup of Plate ID and Plate Position

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.15] - 2024-02-02

### Added

- Global - add pandas_utils module to wrap pandas functions to throw AllotropeConversionError

### Fixed

- Beckman Vi-Cell XR - total cells column no longer required
- Beckman Vi-Cell XR - ignore invalid first row when present
- Thermo Fisher Scientific NanoDrop Eight - capture concentration in files that do not have NA Type column
- Agilent Gen5 - removed hardcoding of date parsing

### Changed

- Spectrophotometry - correct the spectrophotometry/BENCHLING/2023/12 schema to account for feedback from Allotrope Modeling Working Group
- Molecular Devices Softmax Pro - replace null values with N/A

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.14] - 2024-01-31

### Added

- Luminex xPONENT - initial implementation

### Fixed

- Molecular Devices Softmax Pro - ignore calculated data documents entry in output when there are no calculated data documents
- Molecular Devices Softmax Pro - check for raw data indicator in plate header

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.13] - 2024-01-19

### Added

- ChemoMetec NC View - initial implementation
- Thermo Fisher Scientific NanoDrop Eight - initial implementation
- Unchained Labs Lunatic - add calculated data documents
- Molecular Devices Softmax Pro - add calculated data documents
- Multi Analyte Profiling - add multi-analyte-profiling/BENCHLING/2024/01 schema
- Global - add non-numeric options for tQuantityValue value property
- ChemoMetec Nucleoview - Add support for non-numeric values
- Internal - add context manager to handle backups to schema generation script
- Internal - Add --regex argument to schema generation script

### Fixed

- Perkin Elmer Envision - calculated data name now captures string to the left - rather than right - of the ‘=’ in the Formula cell

### Changed

- Molecular Devices Softmax Pro - update plate reader schema
- Global - Standardized on UNITLESS constant ("(unitless)") for unitless values. Changed Perkin Elmer Envision, which formerly used "unitless"
- Perkin Elmer Envision - increase test coverage of calculated data documents

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.12] - 2023-12-12

### Added

- PerkinElmer EnVision - calculated data documents
- Unchained Labs Lunatic - initial implementation

### Fixed

- AppBio QuantStudio RT-PCR - fix per-well calculated documents

### Changed

- AppBio QuantStudio RT-PCR - refactor builders as create methods

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.11] - 2023-12-04

### Added

- Documentation - add parser structure documentation (#108)

### Changed

- Agilent Gen5 - refactor to use explicit dataclasses structure
- Beckman Vi-Cell BLU - update to use cell-counting/BENCHLING/2023/11 schema
- Beckman Vi-Cell XR - update to use the cell-counting/BENCHLING/2023/11 schema
- PerkinElmer EnVision - update use the plate-reader/BENCHLING/2023/09 schema
- Global - standardize and clarify exception messages

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.10] - 2023-11-14

### Added

- Plate Reader - add data system document to plate reader schema

### Changed

- AppBio QuantStudio RT-PCR - redefine reporter dye setting for genotyping experiments (#102)
- Global - update TimeStampParser.parse() to raise for invalid input

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.9] - 2023-11-03

### Added

- AppBio QuantStudio RT-PCR - add missing example outputs for tests
- Cell Counting - add cell-counting/REC/2023/09 schema, with additions to support existing use cases

### Fixed

- Plate Reader - fix plate-reader schema to be compatible with current supported adapters and change REC -> BENCHLING

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.8] - 2023-10-30

### Added

- Internal - allow lines reader to accept or infer encoding

### Fixed

- Global - use fuzzy=True for timestamp parsing to handle non-standard cases (e.g. mixing 24h time and AM/PM)

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.7] - 2023-10-26

### Added

- Internal - add governance document
- Plate Reader - add plate-reader/REC/2023/09 schema (not in use by parsers yet)

### Fixed

### Changed

- Cell Counting - change the schema name of cell-counting/BENCHLING/2023/09 to match Allotrope
- Roche Cedex HiRes - rename to PerkinElmerEnvisionParser and RocheCedexBiohtParser for consistency
- Global - generic Exceptions to AllotropyErrors

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.6] - 2023-10-16

### Added

- AppBio QuantStudio RT-PCR - test for broken calculated document structure

### Fixed

- AppBio QuantStudio RT-PCR - fix bug in result caching

### Changed

- AppBio QuantStudio RT-PCR - allow block type to have plate well count in any position
- Internal - replace datetime.timezone with ZoneInfo in TimestampParser
- Internal - implement CsvReader as child of LinesReader

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.5] - 2023-10-04

### Added

- AppBio AbsoluteQ - initial implementation

### Fixed

- AppBio QuantStudio RT-PCR - redefine calculated data documents references as required
- dPCR - update dPCR schema "experiment type" enum to have correct values

### Changed

- dPCR - make "fluorescence intensity threshold setting" optional in the dPCR schema
- Internal - update the "calculated datum" property on the calculated data documents to allow different units

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.4] - 2023-10-03

### Fixed

- AppBio QuantStudio RT-PCR - remove duplication of calculated documents related to quantity measurements
- qPCR - rename "qPCR detection chemistry" to "PRC detection chemistry" in PCR schemas
- dPCR - add missing @dataclass annotation to TQuantityValueNumberPerMicroliter

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.3] - 2023-10-03

### Fixed

- AppBio QuantStudio RT-PCR - redefine the way calculated documents are structured for relative standard curve
- dPCR - fix some issues in dPCR schema and corresponding model updates
- AppBio QuantStudio RT-PCR - accept comma as thousand indicator in all sections

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.2] - 2023-09-27

### Added

- dPCR - add Digital PCR (dPCR) documents
- AppBio QuantStudio RT-PCR - add calculated documents
- AppBio QuantStudio RT-PCR - add genotyping data structure test

### Fixed

- AppBio QuantStudio RT-PCR - remove typing ignore tags from the construction of structure
- AppBio QuantStudio RT-PCR - ignore unexpected sections in input file
- AppBio QuantStudio RT-PCR - accept comma as thousand indicator in results section

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.1] - 2023-09-22

### Changed

- Internal - loosen requirement for jsonschema package to make allotropy compatible with datamodel-code-generator

## [0.1.89] - 2025-05-20

## [0.1.82] - 2025-04-02

## [0.1.89] - 2025-05-20

## [0.1.0] - 2023-09-18

### Added

- Initial commit, includes support for:
  - Agilent Gen5
  - AppBio QuantStudio
  - Beckman Vi-Cell BLU
  - Beckman Vi-Cell XR
  - Molecular Devices Softmax Pro
  - NovaBio Flex2
  - PerkinElmer Envision
  - Roche Cedex BioHT
