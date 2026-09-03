# Allotropy

Lab instrument data parser library. Converts vendor file formats to Allotrope Simple Model (ASM) JSON format using generated Python dataclass models.

## Quick Reference

```bash
# Run tests
hatch run test_all.py3.10:pytest tests/ -x -q

# Run linting
hatch run lint

# Auto-fix lint
hatch run lint:fmt

# Generate models from schemas
hatch run scripts:generate-schemas \
  "http://purl.allotrope.org/json-schemas/adm/cell-counting/REC/2024/09/cell-counting.schema"

# Release a new version (bumps patch, updates CHANGELOG, creates branch/tag/PR/release)
hatch run scripts:update-version
```

## Releasing

Use `hatch run scripts:update-version` to create a new release. Do NOT use `hatch version` directly. The script:
1. Checks out a clean branch from main (`release-v{version}`)
2. Bumps the patch version in `__about__.py`
3. Updates `CHANGELOG.md` from conventional commit prefixes since last release
4. Commits, pushes, tags, creates a PR and GitHub release

Options:
- `--version/-v X.Y.Z` — set an explicit version instead of auto-incrementing patch
- `--skip_pr` — only update files locally without pushing/creating PR

## Architecture Overview

```
src/allotropy/
├── allotrope/
│   ├── schemas/              # Cached JSON schemas (fetched from upstream or manually placed)
│   ├── models/               # Python dataclasses representing ASM schema types
│   │   ├── adm/              # Generated technique + core models (NEVER manually edit)
│   │   ├── qudt/             # Generated unit models (NEVER manually edit)
│   │   └── shared/           # Shared base types, enums, and components (manually maintained)
│   ├── schema_mappers/      # Map intermediate Data objects → Model instances
│   ├── schema_gen/          # Code generation pipeline (see schema_gen/CLAUDE.md for details)
│   │   ├── generate.py      # Entry point / orchestrator
│   │   ├── codegen/         # JSON schema → Python dataclass generator (package)
│   │   ├── fetcher.py       # Schema fetching + caching + dependency resolution
│   │   ├── naming.py        # URL ↔ Python identifier transformations
│   │   └── serializer.py    # Dataclass ↔ JSON dict round-tripping
│   └── converter.py         # Dispatches parser output through schema mapper to JSON
├── parsers/                  # Vendor-specific file parsers (one package per instrument)
└── types.py                  # Shared type aliases
```

## Schema Mapper Layer

Schema mappers sit between parsers and generated models:

```
Parser (reads vendor file) → intermediate Data dataclass → Mapper.map_model() → Model instance
```

Each mapper defines:
- Intermediate dataclasses (`Data`, `Metadata`, `Measurement`, `MeasurementGroup`, etc.)
- A `Mapper` class extending `SchemaMapper[Data, Model]` with `map_model()` method
- The `MANIFEST` URL string for the `field_asm_manifest` field

## Field Naming Conventions

Generated models use these naming patterns:

| JSON Name | Python Field |
|-----------|-------------|
| `$asm.manifest` | `field_asm_manifest` |
| `ASM file identifier` | `asm_file_identifier` |
| `UNC path` | `unc_path` |
| `pH` | `p_h` |
| `pO2` | `p_o2` |
| `pCO2` | `p_co2` |

Quantity value types use abbreviated unit names: `TQuantityValueDegC`, `TQuantityValueMAU`, `TQuantityValueMmHg`, `TQuantityValueMicroLPermin`, `TQuantityValueM`, `TQuantityValueNM`, `TQuantityValueM1s1`, `TQuantityValueS1`, `TQuantityValueRU`, `TQuantityValueS`.

## Vendor Auto-Discovery

Each parser has a `sniff(cls, named_file_contents) -> bool` classmethod used by `discover_vendor()` to auto-detect the correct parser for a file. The discovery logic in `parser_factory.py`:

1. Filters candidates by file extension
2. Calls `sniff()` on each — collects all matches
3. Single match: returns immediately
4. Multiple matches: tries `create_data()` on each to disambiguate
5. No sniff matches: tries `create_data()` on all candidates as fallback
6. If sniff matched but parse failed: trusts the sniff result

**When adding a new parser:**
- Implement `sniff()` — check file headers, sheet names, XML root tags, etc. Keep it lightweight.
- If the file extension is unique to this parser (e.g. `.blr`, `.rslt`), `return True` is fine.
- For shared extensions (`.csv`, `.txt`, `.xlsx`), check distinctive content patterns.
- **Check sniff logic of related parsers** that share the same extension — your new sniff must not false-positive on their test files, and theirs must not match yours.
- Run `hatch run test_all.py3.10:pytest tests/discover_vendor_test.py -x -q` to verify.
- Handle encoding: many files use UTF-16 LE (BOM `\xff\xfe`). Decode appropriately before text checks.

## Test Data

Sample files are usually **real customer exports**. Never commit one as received — always derive a fixture from it, and keep the original out of the repo.

### 1. Anonymize every customer-unique identifier

Replace all of them, not just the obvious names. Preserve each value's *shape* (length, separators, token count) so the parser behaves the same, and apply every replacement consistently across all files in the bundle:

- Instrument, site, and project names; operator, user, and client names
- Serial numbers, part numbers, asset tags, barcodes
- Sample, compound, and method names
- Absolute file paths — these usually embed a username and project name (e.g. `C:\CDSProjects\jdtest\Results\...`)
- GUIDs and internal record IDs

**Some identifiers are load-bearing** — the parser matches on them, and renaming one side of a reference silently breaks the fixture. Examples: in `.rslt` bundles the ACAML `TraceID` GUIDs must equal the `.dx` member filenames, and signal names like `DAD1A,Sig=280,4 Ref=off` are parsed for detector wavelength and bandwidth. Rename such values across every reference at once, or leave them alone.

Shape matters for behavior too: an instrument name of `Kaisla` and one of `Luxo HPLC` take different code paths, because `brand_name` reads the second whitespace token.

Before committing, grep the fixture **and** the generated expected JSON for every customer string you know of.

### 2. Trim to a representative sample

Keep only enough data to exercise the code being added or fixed. Aim for KBs, not MBs — the full-size real-world file is not a fixture.

- **Drop container members the parser never reads.** Check what it actually opens: an OpenLab CDS `.dx` is ~75 MB but only `injection.acmd`, the `.CH` chromatograms, and one pressure `.IT` are read; the `.UV` spectral member is 95% of the bytes and is ignored.
- **Cut repeated records** — 2 injections/wells/rows instead of 10 — and downsample long data series.
- **Keep list-shaped XML at 2+ elements.** `xmltodict` maps a single repeated element to a dict rather than a list, so trimming a section to one entry breaks any code that indexes it.
- **Prefer deriving from an existing anonymized fixture** when the new case is a metadata variation (an absent optional element, a different enum) rather than a new binary layout. That reintroduces zero customer data and is usually smaller.

### 3. Verify and generate

- **Confirm the fixture is real coverage.** Stash the source fix, run the test, and check it fails for the expected reason; then restore. A fixture that passes either way tests nothing.
- **Generate expected JSON with `--overwrite`**, never by hand: `hatch run test_all.py3.10:pytest tests/parsers/{name}/ --overwrite -q`. The framework mocks UUID generation to produce deterministic IDs (`{VENDOR}_TEST_ID_0`); hand-generated JSON has random UUIDs and will never match. The first run fails while writing the file — that is expected. Add only the input file, then run it.
- **Never modify existing expected JSON** to make a change pass. If a refactor alters existing output, the code is wrong. Check with `git diff main -- 'tests/parsers/*/testdata/*.json'`; only an intentional behavior change justifies a diff, and it belongs in the PR description.

## Code Rules

- **No runtime imports.** All imports must be at module level. Never put `import` or `from ... import` inside a function body to work around circular dependencies — fix the dependency instead.
