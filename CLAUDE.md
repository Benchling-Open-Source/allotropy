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

# Generate models from schemas (pass all schemas sharing the same core version together)
hatch run scripts:generate-schemas \
  "http://purl.allotrope.org/json-schemas/adm/cell-counting/REC/2024/09/cell-counting.schema" \
  "http://purl.allotrope.org/json-schemas/adm/absorbance/REC/2024/09/absorbance-cube-detector.schema" \
  ...
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
│   ├── schema_gen/          # Code generation pipeline
│   │   ├── generate.py      # Entry point / orchestrator
│   │   ├── codegen.py       # JSON schema → Python dataclass generator
│   │   ├── fetcher.py       # Schema fetching + caching + dependency resolution
│   │   ├── naming.py        # URL ↔ Python identifier transformations
│   │   └── serializer.py    # Dataclass ↔ JSON dict round-tripping
│   └── converter.py         # Dispatches parser output through schema mapper to JSON
├── parsers/                  # Vendor-specific file parsers (one package per instrument)
└── types.py                  # Shared type aliases
```

## Schema Generation Pipeline

### Pipeline Flow

```
Schema URLs → fetch (fetcher.py) → merge BENCHLING embeds (generate.py)
  → topological sort → generate units (custom) → generate models (codegen.py)
  → patch JsonFloat → lint (ruff + black) → write .py files
```

### Running the Generator

Generation is idempotent — each schema can be run independently or together. Shared modules (core.py, hierarchy.py) produce identical output regardless of which technique schema triggers their generation. Passing multiple schemas together is supported but not required.

```bash
# Single schema
hatch run scripts:generate-schemas \
  "http://purl.allotrope.org/json-schemas/adm/cell-counting/REC/2024/09/cell-counting.schema"

# Multiple schemas together (also works)
hatch run scripts:generate-schemas \
  "http://purl.allotrope.org/json-schemas/adm/cell-counting/REC/2024/09/cell-counting.schema" \
  "http://purl.allotrope.org/json-schemas/adm/pcr/REC/2024/09/qpcr.schema"
```

### Schema Types

| Type | URL Pattern | Source | Editable? |
|------|-------------|--------|-----------|
| **REC** (Recommendation) | `.../REC/YYYY/MM/...` | Fetch from upstream purl | NO — must match upstream exactly |
| **WD** (Working Draft) | `.../WD/YYYY/MM/...` | Manual or fetched | YES — pre-release, may need fixes |
| **BENCHLING** | `.../BENCHLING/YYYY/MM/...` | Manual placement | YES — vendor-specific extensions |

### BENCHLING Schema Handling

BENCHLING schemas embed modified copies of dependency schemas as URL-keyed `$defs` entries. The generator handles this in two steps:

1. **Merge**: Deep-merge BENCHLING's embedded additions (e.g., extra properties) into the standalone dependency schemas
2. **Strip**: Remove URL-keyed `$defs` so codegen resolves `$ref`s to external schema files

This preserves custom fields (like `compartment temperature`) while keeping the modular output structure.

### Generated Model Structure

```
models/
├── shared/                                # Shared base types (manually maintained, NOT generated)
│   ├── definitions/
│   │   ├── definitions.py                 # TQuantityValue, TDatacube, JsonFloat, TStatisticDatumRole, etc.
│   │   ├── quantity_values.py             # TQuantityValue{Unit} thin subclasses (centralized)
│   │   └── units.py                       # HasUnit + unit subclasses
│   └── components/
│       └── plate_reader.py                # ContainerType, SampleRoleType enums
├── qudt/rec/_YYYY/_MM/units.py            # HasUnit + unit subclasses (generated, per core version)
├── adm/core/rec/_YYYY/_MM/
│   ├── core.py                            # Core types + re-exports of TQuantityValue{Unit} from shared
│   ├── hierarchy.py                       # DataSystemDocument, SampleDocument, aggregate docs
│   └── cube.py                            # TDatacube, TDatacubeStructure, array types
└── adm/{technique}/{status}/_YYYY/_MM/
    └── {technique}.py                     # Model + technique-specific classes (imports from core)
```

**Dependency chain**: `shared/` → `units.py` → `core.py` → `cube.py` → `hierarchy.py` → `{technique}.py`

**Shared module**: Base types in `shared/definitions/definitions.py` (TQuantityValue, TDatacube, JsonFloat, etc.) are manually maintained and imported by generated modules rather than regenerated per core version. The codegen imports these via `_SHARED_DEFINITION_TYPES` and generates TQuantityValue subclasses in `shared/definitions/quantity_values.py` to avoid duplication across core versions.

## Codegen Internals (codegen.py)

### Key Classes

- **`SchemaCodeGenerator`** — Main engine. Holds all schemas + modules, generates in dependency order.
- **`ModuleCode`** — Represents a single .py file: imports, classes, exported names. Handles deduplication and topological sorting of classes.
- **`GeneratedClass`** — A single class or type alias with its code string.
- **`ImportEntry`** — A `from module import Name` statement.

### Type Dispatch (`_generate_type`)

The generator dispatches based on schema structure:

| Schema Pattern | Handler | Output |
|----------------|---------|--------|
| `oneOf` | `_generate_one_of()` | Union type (often `primitive \| TypedItem`) |
| `anyOf` | `_generate_any_of()` | Union of all variants |
| `enum` | `_generate_enum()` | Enum class (>1 value) or `Literal[...]` (single value) |
| `object` + `properties` | `_generate_dataclass()` | Frozen dataclass |
| `allOf` (at def level) | `_generate_all_of_def()` | Merged dataclass with inheritance |
| `$ref` (at def level) | — | Type alias |
| `array` + `items` | — | `list[ItemType]` alias |

### allOf Composition Patterns

allOf is the most complex part. In properties, it resolves to:

| Pattern | Example | Result |
|---------|---------|--------|
| `allOf[tQuantityValue, unit_ref]` | `osmolality` | `TQuantityValueMosmPerKg` thin subclass |
| `allOf[tQuantityValue, {oneOf: [unit1, unit2]}]` | Multi-unit field | `TQuantityValueX \| TQuantityValueY` |
| `allOf[tClass, {enum: [...]}]` | `sample_role_type` | Enum class (>1 value) or `Literal[...]` (single value) |
| `allOf[base_ref, {properties: {...}}]` | Technique overrides | Merged inline class |

### Quantity Value Types (Thin Subclasses)

Generated in the **core module**, not technique modules:

```python
@dataclass(frozen=True, kw_only=True)
class TQuantityValueMAU(TQuantityValue):
    unit: str = "mAU"
```

When a technique schema references `allOf[tQuantityValue, mAU_unit]`, the codegen:
1. Checks if `TQuantityValueMAU` already exists in core module
2. If not, generates it there
3. Adds an import to the technique module

This prevents duplication across technique modules that share the same unit.

### json_name Metadata

Fields only get `metadata={"json_name": "..."}` when the JSON name isn't a trivial space-to-underscore mapping:

```python
# No metadata needed: "device system document" → device_system_document
device_system_document: TStringValue | None = None

# Metadata needed: "$asm.manifest" → field_asm_manifest
field_asm_manifest: str = field(metadata={"json_name": "$asm.manifest"})

# Metadata needed: "cube-structure" → cube_structure (hyphen, not space)
cube_structure: TDatacubeStructure | None = field(default=None, metadata={"json_name": "cube-structure"})

# Metadata needed: "pCO2" → p_co2 (camelCase conversion)
p_co2: TQuantityValueMmHg | None = field(default=None, metadata={"json_name": "pCO2"})
```

**Rule**: `needs_json_name = json_name != python_name.replace("_", " ")`

### Deep Merge Semantics

`_deep_merge_schemas(base, overlay, any_of=False)` handles two modes:

- **Normal merge** (`any_of=False`): `required` fields are unioned (accumulated)
- **anyOf merge** (`any_of=True`): `required` fields are intersected (only required if ALL variants require it)

This is critical for the detector measurement pattern where anyOf variants contribute optional fields from different detector sub-schemas.

### Constraint-Only Overlays

Properties with only validation keywords (`required`, `minItems`, `maxItems`, `minimum`, etc.) but no structural type info are skipped — they refine a base-class field, not define new types. `_resolve_property_type()` returns `None` for these.

### Reference Resolution

- **Local refs** (`#/$defs/X`): Look up in current schema's `$defs`
- **External refs** (`http://...schema#/$defs/X`): Look up in the already-generated module for that schema URL, add import
- **Forward references**: Handled by `from __future__ import annotations` (string annotations)

## Serializer (serializer.py)

Converts between dataclass instances and JSON dicts:

- **`to_dict(obj)`**: Dataclass → JSON dict. Uses `metadata["json_name"]` or falls back to `field_name.replace("_", " ")`
- **`from_dict(data, cls)`**: JSON dict → dataclass instance. Builds reverse mapping.

**Important**: The fallback `field_name.replace("_", " ")` in the serializer must match the codegen's rule for when to omit `json_name` metadata. If these diverge, serialization breaks silently.

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

## Debugging Tips

### "Class X not found in module Y"
The module wasn't generated yet when the technique schema tried to import. Check that `build_dependency_order()` places Y before the technique schema. All schemas sharing a core version must be passed together.

### "Field missing from generated model"
1. Check the JSON schema for the field — is it in `properties`?
2. If it's in an `allOf` overlay, check `_resolve_all_of_property()` handles the pattern
3. For BENCHLING schemas: verify the merge step preserved the embedded additions
4. For anyOf compositions: fields from variants become optional (intersected required)

### "Wrong json_name / serialization mismatch"
Compare the codegen rule (`json_name != python_name.replace("_", " ")`) with the serializer fallback (`f.name.replace("_", " ")`). They must agree on when metadata is needed.

### "Duplicate class in generated output"
Recursive schemas can generate the same inline class from multiple locations. `ModuleCode.render()` deduplicates by merging fields from duplicates. Check `_merge_class_fields()`.

### "Quantity type not generated"
The `allOf[tQuantityValue, unit_ref]` pattern must be recognized by `_resolve_all_of_property()`. If the unit ref points to a missing unit in the units schema, the type won't generate. Check the units.schema.json has the required unit definition.

### "Empty generated model file"
Tabular schemas (e.g., `mass-spectrometry.tabular.schema`) use flat `properties` without allOf+hierarchy composition. The codegen doesn't handle these — they produce empty output. These schemas are not supported.
