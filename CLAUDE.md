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
```

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

## Code Rules

- **No runtime imports.** All imports must be at module level. Never put `import` or `from ... import` inside a function body to work around circular dependencies — fix the dependency instead.
