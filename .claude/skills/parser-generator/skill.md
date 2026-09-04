---
name: parser-generator
description: |
  Generate complete Allotropy instrument parsers from example input files. This skill analyzes file structure, auto-detects appropriate Allotrope schemas, and generates fully functional parser code including reader, structure, schema mapper, and tests. Use when creating new parsers for scientific instruments that output data files (Excel, TXT, CSV, binary formats) that need conversion to Allotrope ASM format.
---

# Allotropy Parser Generator

Generate complete, production-ready parsers for scientific instrument data files.

## Quick Start Workflow

1. **Analyze input file** - Run analysis script to detect structure and schema
2. **Review suggestions** - Confirm or override detected schema
3. **Generate parser** - Create complete parser with all files
4. **Test and validate** - Run tests to ensure correctness
5. **Register parser** - Add to parser factory

## Step 1: Analyze Input File

Always start by analyzing the example input file:

```bash
python scripts/analyze_file.py <path_to_example_file>
```

This script:
- Detects file format (Excel, TXT, CSV, binary)
- Identifies measurement types (absorbance, pH, CT values, etc.)
- Suggests appropriate Allotrope schema
- Shows file structure overview

Example output:
```
============================================================
FILE ANALYSIS: example_data.xlsx
============================================================
format: excel
shape: (150, 12)
suggested_schema: plate-reader
measurement_indicators: ['absorbance', 'well', 'plate']

============================================================
✅ RECOMMENDED SCHEMA: plate-reader
============================================================
```

## Step 2: List Available Schemas

Review available schemas if auto-detection needs override:

```bash
# From within allotropy repository
python scripts/list_schemas.py [optional_filter]

# Use --verbose for detailed output with schema paths
python scripts/list_schemas.py --verbose
```

The script dynamically scans your local allotropy repository for all available schemas and shows:
- Schema technique names (plate-reader, pcr, etc.)
- All available schema versions and paths
- Description and use cases
- Example parsers that use each schema

## Step 3: Generate Parser Code

Use the `create_parser.py` script to generate the complete parser:

```bash
python scripts/create_parser.py <parser_name> <schema_regex> --display_name "Vendor Instrument" --detection_modes "Absorbance, Fluorescence"
```

The `--detection_modes` flag sets the `SUPPORTED_DETECTION_MODES` class attribute, which populates the instruments table. Use comma-separated values for multiple modes (e.g. `"Absorbance, Fluorescence, Luminescence"`). Omit for instruments without detection (liquid handlers).

### Parser Structure Created

```
src/allotropy/parsers/{parser_name}/
├── __init__.py                          # Exports parser class
├── {parser_name}_parser.py              # VendorParser subclass
├── {parser_name}_reader.py              # File format parser
├── {parser_name}_structure.py           # Dataclasses and factories
├── constants.py                         # Constants (if needed)
└── README.md                            # Documentation

tests/parsers/{parser_name}/
├── __init__.py
├── test_{parser_name}_parser.py         # Test file
└── testdata/
    └── example.xlsx                     # Example test file
```

## Code Generation Approach

### Reader Generation

Based on file format detection:

**Excel files**:
- Use `read_excel` with calamine engine
- Detect header/data sections using markers
- Handle well plate layouts if present
- Extract metadata and measurements

**Text files**:
- Detect delimiter (tab, comma)
- Identify section markers (`[Section]` patterns)
- Parse using `SectionLinesReader` or `read_csv`

### Structure Generation

Create dataclasses for:
- `Header` - Metadata from file header
- `Measurement` - Individual measurement data
- Helper functions:
  - `create_metadata()` - Build Metadata object
  - `create_measurement_groups()` - Build MeasurementGroup list
  - `create_calculated_data()` - Build calculated data (if applicable)

### Measurement Grouping — match the existing parsers for that schema

`MeasurementGroup` becomes one technique document (e.g. one `qpcr document`); each
`Measurement` inside it becomes one `measurement document`. **Inverting this nesting is
the most common structural error in a new parser** — many measurement groups holding one
measurement each, where the convention is one group holding many measurements (or vice
versa). Nothing catches it automatically: the ASM output is schema-valid either way, and
`--overwrite` cheerfully writes the wrong shape as the expected JSON, so the test passes
and the parser ships producing output that doesn't line up with every other parser for
that schema.

**Before writing `create_measurement_groups()`, derive the convention from the parsers
that already use the same schema mapper:**

1. Find them:
   ```bash
   grep -rl "schema_mappers.adm.{technique}" src/allotropy/parsers/
   ```
2. Read each one's `create_measurement_groups()` and note **what one group represents** —
   the grouping key (a well, a sample, an injection, a plate) and what varies between the
   measurements within a group.
3. Confirm it empirically against their committed expected JSON with the check below, then
   run the same check on your new parser's output and require the same shape.

If your parser's shape legitimately differs (the instrument reports something the others
don't), say so explicitly in the PR description with the reason. Do not silently diverge.

#### Known conventions

| Schema mapper | One `MeasurementGroup` (technique document) | One `Measurement` (measurement document) |
|---|---|---|
| `adm.pcr.rec._2024._09.qpcr` | **one well** | **one target / reporter-dye channel within that well** |

Verified across all committed expected JSON for `appbio_quantstudio`,
`appbio_quantstudio_designandanalysis`, `cfxmaestro`, and `thermo_fisher_diomni`: every
`qpcr document` covers exactly one well, no well is split across two documents, and a
document holds 1–4 measurements — one per target. Source rows in these files are usually
one-per-target, so grouping is explicit:

```python
for _, well_data in measurements_data.groupby("Well"):
    measurements = [_create_measurement(row) for _, row in well_data.iterrows()]
    measurement_groups.append(MeasurementGroup(measurements=measurements, ...))
```

Anti-pattern for qPCR — one group per source row, yielding N single-measurement `qpcr
document`s for the same well:

```python
# WRONG for qPCR: inverts the nesting
for _, row in measurements_data.iterrows():
    groups.append(MeasurementGroup(measurements=[_create_measurement(row)], ...))
```

When a target column is absent (CFX Maestro reports `target DNA description` as `N/A`),
measurements within the well are still one-per-fluorophore, distinguished by
`reporter_dye_setting`. Group by well regardless.

For any other schema, fill in the convention by inspecting existing parsers — do not
assume it matches qPCR. Grouping keys differ by technique.

#### Checking document nesting

Run this against existing parsers' expected JSON to learn the convention, and against
yours to verify it matches:

```bash
python3 - tests/parsers/{parser_name}/testdata/*.json <<'EOF'
import collections, json, sys

for path in sys.argv[1:]:
    doc = json.load(open(path))
    agg = [v for k, v in doc.items() if k.endswith("aggregate document")][0]
    docs = [v for k, v in agg.items() if k.endswith("document") and isinstance(v, list)][0]
    n_meas, groups = collections.Counter(), []
    for d in docs:
        mds = d["measurement aggregate document"]["measurement document"]
        n_meas[len(mds)] += 1
        groups.append({md.get("sample document", {}).get("well location identifier") for md in mds})
    multi = sum(1 for g in groups if len(g) > 1)
    singles = [next(iter(g)) for g in groups if len(g) == 1]
    dupes = [w for w, c in collections.Counter(singles).items() if c > 1]
    print(f"{len(docs):>5} technique docs | measurements/doc {dict(sorted(n_meas.items()))} "
          f"| docs spanning >1 well: {multi} | wells in >1 doc: {len(dupes)} | {path.split('/')[-1]}")
EOF
```

For qPCR, both `docs spanning >1 well` and `wells in >1 doc` must be `0`, and
`measurements/doc` should equal the number of targets per well in the source file. If you
see `measurements/doc {1: N}` where the input has multiple targets per well, the nesting
is inverted.

### Parser Generation

Generate `VendorParser` subclass with:
- `DISPLAY_NAME` - User-friendly instrument name
- `RELEASE_STATE` - Start with `ReleaseState.WORKING_DRAFT`
- `SUPPORTED_EXTENSIONS` - File extensions (from analysis)
- `SUPPORTED_DETECTION_MODES` - Detection modes the parser supports (e.g. `"Absorbance, Fluorescence"`) or `None` for instruments without detection (e.g. liquid handlers). This populates the "Supported Detection Modes" column in the supported instruments table.
- `SCHEMA_MAPPER` - Reference to schema mapper
- `create_data()` - Orchestrate reader + structure → Data

## Step 4: Schema Mapping

The schema mapper defines the intermediate `Data` structure and maps it to Allotrope models.

### If Schema Mapper Exists

Reuse existing mapper:
```python
from allotropy.allotrope.schema_mappers.adm.{technique}.{org}.{year}.{month}.{technique} import (
    Data,
    Mapper,
)
```

Conform your `create_data()` to return the expected `Data` structure.

### If Schema Mapper Needs Creation

This is rare - most techniques have existing mappers. If needed:

1. Define Data structure matching schema requirements
2. Implement `Mapper.map_model()` method
3. Handle quantity conversions and units

## Step 5: Testing

Generate test file:

```python
# tests/parsers/{parser_name}/test_{parser_name}_parser.py

def test_to_allotrope_{parser_name}() -> None:
    test_file = "testdata/example.xlsx"
    expected_file = "testdata/example.json"
    run_allotropy(test_file, expected_file)
```

Run tests:
```bash
hatch run test:pytest tests/parsers/{parser_name}/
```

## Step 6: Register Parser

Add to `src/allotropy/parser_factory.py`:

1. Import your parser:
```python
from allotropy.parsers.{parser_name}.{parser_name}_parser import {ParserName}Parser
```

2. Add to `Vendor` enum:
```python
class Vendor(Enum):
    YOUR_INSTRUMENT = "YOUR_INSTRUMENT"
```

3. Add to `_VENDOR_TO_PARSER` mapping:
```python
_VENDOR_TO_PARSER: dict[Vendor, type[VendorParser]] = {
    Vendor.YOUR_INSTRUMENT: YourInstrumentParser,
    # ... existing parsers
}
```

## Implementation Checklist

- [ ] Analyze example input file with `analyze_file.py`
- [ ] Confirm or select schema with `list_schemas.py`
- [ ] Generate parser using `create_parser.py`
- [ ] Review and adjust generated code
- [ ] Determine the `MeasurementGroup` / `Measurement` convention from existing parsers for
      the same schema mapper, and match it (see "Measurement Grouping")
- [ ] Set `SUPPORTED_DETECTION_MODES` to the correct value for the instrument
- [ ] Add example test data to `testdata/`
- [ ] Run tests and validate output
- [ ] Run the document-nesting check on the generated JSON and confirm it matches the other
      parsers for that schema
- [ ] Register parser in `parser_factory.py`
- [ ] Run `hatch run scripts:update-instrument-table` to regenerate the supported instruments table
- [ ] Update `RELEASE_STATE` when stable

## Key Design Principles

1. **Follow existing patterns** - Look at similar parsers for guidance. For anything that
   shapes the ASM output — above all the `MeasurementGroup` / `Measurement` nesting — the
   parsers already using that schema mapper are the specification, not a suggestion.
2. **Reuse utilities** - Use `read_excel`, `SeriesData`, `quantity_or_none`, etc.
3. **Type safety** - Use proper quantity types for all measurements
4. **Error handling** - Capture errors in Error objects, don't fail silently
5. **Validation** - Test against real files and validate ASM output

## Common Measurement Types → Schema Mapping

- **Absorbance, fluorescence, luminescence in wells** → `plate-reader`
- **CT/Cq values, amplification curves** → `pcr` (qpcr or dpcr)
- **pH, osmolality, particle size, pO2/pCO2** → `solution-analyzer`
- **Cell density, viability, cell counts** → `cell-counting`
- **Wavelength scans, UV-Vis spectra** → `spectrophotometry`
- **DNA/RNA/protein bands, lanes** → `electrophoresis`
- **Retention time, chromatogram peaks** → `liquid-chromatography`
- **Binding kinetics, SPR responses** → `binding-affinity`
- **Flow cytometry markers, populations** → `flow-cytometry`

## Generating Test Expected Output (JSON files)

**IMPORTANT**: Never manually generate expected JSON output files using `allotrope_from_file()` directly. The test framework uses a UUID mocking mechanism that replaces random UUIDs with deterministic test IDs (e.g., `BECKMAN_PHARMSPEC_TEST_ID_0`). Manually generated JSON will have random UUIDs that won't match the test IDs at comparison time.

**Correct procedure to generate expected output for new test data files:**

1. Place the input test file(s) (e.g., `.xls`, `.xlsx`, `.csv`) in the `tests/parsers/{parser_name}/testdata/` directory
2. Do NOT create the corresponding `.json` file manually
3. Run the tests with `--overwrite` flag — the framework will write the expected output:
   ```bash
   hatch run test_all.py3.10:pytest tests/parsers/{parser_name}/ --overwrite -q
   ```
4. The first run will fail with `AssertionError: Missing expected output file ... writing expected output because 'write_actual_to_expected_on_fail=True'` — this is expected behavior, it means the JSON was written
5. Run the tests again to verify they pass:
   ```bash
   hatch run test_all.py3.10:pytest tests/parsers/{parser_name}/ -q
   ```

The test framework (in `src/allotropy/testing/utils.py`) uses `mock_uuid_generation(vendor.name)` which patches the UUID generator to produce sequential test IDs like `{VENDOR_NAME}_TEST_ID_0`, `{VENDOR_NAME}_TEST_ID_1`, etc. This ensures deterministic output for comparison.

**After generating the JSON, manually inspect it** to verify all expected data from the original input file is present and correct. The test framework only guarantees the parser ran without errors — it cannot verify that all data was captured. Check:
- All measurement values match the source file (spot-check particle sizes, counts, concentrations, etc.)
- Metadata fields are populated correctly (sample name, operator, date/time, serial numbers)
- The correct number of measurements/runs/groups appear (e.g., if the input has 4 runs, the output should have 4 measurement documents)
- **Document nesting matches the other parsers for this schema** — run the check in
  "Checking document nesting" against your output *and* against an existing parser's
  expected JSON, and compare. `--overwrite` will happily write an inverted structure.
- Calculated data (averages, etc.) is present if the source file includes it
- No fields are unexpectedly null or missing

## Troubleshooting

**Schema detection fails**: Manually specify schema after reviewing `list_schemas.py` output

**File format unclear**: Look at similar parsers in the repository

**Mapping errors**: Check schema mapper Data structure requirements

**Tests fail**: Validate ASM output structure matches expected schema