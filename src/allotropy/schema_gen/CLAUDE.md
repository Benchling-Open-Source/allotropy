# Schema Generation Pipeline

## Pipeline Flow

```
Schema URLs → _fetch_all_schemas (fetcher.py)
  → _prepare_benchling_schemas (fork shared deps)
  → _build_generation_order (topological sort)
  → _generate_and_write (codegen/ → _write_and_lint → .py files)
```

## Running the Generator

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

## Schema Types

| Type | URL Pattern | Source | Editable? |
|------|-------------|--------|-----------|
| **REC** (Recommendation) | `.../REC/YYYY/MM/...` | Fetch from upstream purl | NO — must match upstream exactly |
| **WD** (Working Draft) | `.../WD/YYYY/MM/...` | Manual or fetched | YES — pre-release, may need fixes |
| **BENCHLING** | `.../BENCHLING/YYYY/MM/...` | Manual placement | YES — vendor-specific extensions |

## BENCHLING Schema Handling

BENCHLING schemas embed modified copies of REC/WD dependency schemas as URL-keyed `$defs` entries (keys are full `http://` URLs). These copies may add extra properties not in the originals. The generator handles this via `_fork_benchling_shared_schemas()`:

1. **Fork**: For each REC/WD shared schema that a BENCHLING technique modifies, create a BENCHLING-versioned copy (deep-merging the REC base with BENCHLING additions). E.g., `core/REC/2024/09/hierarchy.schema` → `core/BENCHLING/2024/09/hierarchy.schema`
2. **Rewrite**: Update `$ref` strings in BENCHLING schemas to point to the forked BENCHLING versions instead of the original REC ones
3. **Strip**: Remove URL-keyed `$defs` so codegen resolves `$ref`s to external schema files

**Critical invariant**: REC shared schemas are NEVER modified by BENCHLING additions. BENCHLING-specific types (e.g., `CalibrationAggregateDocument`, `ReferenceMaterialDocument`) only appear in BENCHLING-versioned shared modules. This ensures single-schema REC generation produces identical output to full generation.

## Generated Model Structure

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
├── adm/core/benchling/_YYYY/_MM/          # BENCHLING-versioned shared modules (forked from REC)
│   ├── core.py                            # Same structure as REC, may have additional types
│   ├── hierarchy.py
│   └── cube.py
└── adm/{technique}/{status}/_YYYY/_MM/
    └── {technique}.py                     # Model + technique-specific classes (imports from core)
```

**Dependency chain**: `shared/` → `units.py` → `core.py` → `cube.py` → `hierarchy.py` → `{technique}.py`

**Shared module**: Base types in `shared/definitions/definitions.py` (TQuantityValue, TDatacube, JsonFloat, etc.) are manually maintained and imported by generated modules rather than regenerated per core version. The codegen imports these via `SHARED_DEFINITION_TYPES` and generates TQuantityValue subclasses in `shared/definitions/quantity_values.py` to avoid duplication across core versions.

## Codegen Package (`codegen/`)

The codegen package is split into focused modules with a clear dependency hierarchy:

```
codegen/
├── __init__.py          # Public re-exports (backward-compatible API surface)
├── ir.py                # IR types: FieldDef, GeneratedClass, ImportEntry, ModuleCode
│                        #   + helpers: quote_python_literal, _field_declaration,
│                        #   _deduplicate_classes, _topological_sort_classes, etc.
├── merger.py            # SchemaMerger + pure merge functions
│                        #   (_deep_merge_schemas, _strip_required_recursive,
│                        #    _absolutize_refs, _merge_props_into)
├── quantity_values.py   # QuantityValueManager + is_quantity_value_variant
├── type_resolver.py     # TypeResolver + ASM_METADATA_PREFIXES, extract_unit_const,
│                        #   SHARED_DEFINITION_TYPES, SHARED_DEFINITIONS_MODULE
└── generator.py         # SchemaCodeGenerator (orchestrator)
```

**Dependency order**: `ir` → `merger` → `quantity_values` → `type_resolver` → `generator`. Each module only imports from modules above it in this chain (plus `naming.py`).

### Key Classes

- **`SchemaCodeGenerator`** (`generator.py`) — Module-level orchestrator. Pre-computes a static `_export_map` of `{schema_url: {def_name: class_name}}` before code generation starts, then iterates schemas in dependency order, handling shared definition re-exports, ADM root flattening. Delegates type generation to `TypeResolver`.
- **`TypeResolver`** (`type_resolver.py`) — Type resolution engine. All schema-to-type mapping: dispatch on schema patterns, property resolution, `$ref` resolution, quantity value generation. Uses the pre-computed `_export_map` for cross-module name resolution (no dependency on generation order).
- **`SchemaMerger`** (`merger.py`) — Merges properties from variant sub-schemas (anyOf/oneOf composition). Pure schema-level operations, independent of code generation.
- **`QuantityValueManager`** (`quantity_values.py`) — Tracks TQuantityValue{Unit} thin subclasses. Maps unit strings to class names, records new classes for `generate.py` to append.
- **`ModuleCode`** (`ir.py`) — Represents a single .py file: imports, classes, exported names. Handles deduplication and topological sorting of classes.
- **`GeneratedClass`** (`ir.py`) — IR for a single class, type alias, or enum. Has `fields`, `enum_members`, or `alias_target` (at most one populated).
- **`ImportEntry`** (`ir.py`) — A `from module import Name` statement.

### Cross-Module Name Resolution

`SchemaCodeGenerator._analyze_exports()` builds a complete, immutable mapping of every schema's exported names before any code generation starts. `TypeResolver._resolve_ref_type()` uses this static `_export_map` instead of reading from the mutable `_modules` dict, so name resolution is independent of the order modules are generated. The `_modules` dict is an output-only accumulator.

### Type Dispatch (`TypeResolver.generate_type`)

The type resolver dispatches based on schema structure:

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

Centralized in `shared/definitions/quantity_values.py`, not generated per-module:

```python
@dataclass(frozen=True, kw_only=True)
class TQuantityValueMAU(TQuantityValue):
    unit: str = "mAU"
```

When a technique schema references `allOf[tQuantityValue, mAU_unit]`, the codegen:
1. Resolves the unit const value from the units schema `$defs`
2. Asks `QuantityValueManager.get_or_create()` for the class name
3. Adds an import from `shared/definitions/quantity_values` to the consuming module
4. If the class is new, `generate.py` appends it to `quantity_values.py` after generation

This prevents duplication across technique modules and core versions that share the same unit.

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

Properties with only validation keywords (`required`, `minItems`, `maxItems`, `minimum`, etc.) but no structural type info are skipped — they refine a base-class field, not define new types. Detected by `_is_constraint_only_overlay()`, which checks that the schema keys are a subset of `_CONSTRAINT_ONLY_KEYS`. Empty schemas are NOT overlays (they're real `Any` fields). `_resolve_property_type()` returns `None` for these.

### Reference Resolution

- **Local refs** (`#/$defs/X`): Look up in current schema's `$defs`
- **External refs** (`http://...schema#/$defs/X`): Look up in the pre-computed `_export_map` for that schema URL, add import
- **Forward references**: Handled by `from __future__ import annotations` (string annotations)

## Serialization (converter.py)

Serialization lives in `src/allotropy/allotrope/converter.py`:

- **`unstructure(obj)`**: Dataclass → JSON dict. Uses `metadata["json_name"]` or falls back to `field_name.replace("_", " ")`
- **`structure(data, cls)`**: JSON dict → dataclass instance. Builds reverse mapping.

These are fully reversible: `structure(unstructure(x), type(x)) == x` always holds.

**Important**: The fallback `field_name.replace("_", " ")` in `unstructure`/`structure` must match the codegen's rule for when to omit `json_name` metadata. If these diverge, serialization breaks silently.

## Debugging Tips

### "Class X not found in module Y"
The export map is pre-computed, so this usually means the schema URL wasn't included in the generation run. Check that `_build_generation_order()` includes Y and that its `$defs` contain the expected definition name.

### "Field missing from generated model"
1. Check the JSON schema for the field — is it in `properties`?
2. If it's in an `allOf` overlay, check `_resolve_all_of_property()` handles the pattern
3. For BENCHLING schemas: verify the fork step created a BENCHLING-versioned shared schema with the embedded additions
4. For anyOf compositions: fields from variants become optional (intersected required)

### "Wrong json_name / serialization mismatch"
Compare the codegen rule (`json_name != python_name.replace("_", " ")`) with the converter fallback (`f.name.replace("_", " ")`). They must agree on when metadata is needed.

### "Duplicate class in generated output"
Recursive schemas can generate the same inline class from multiple locations. `_deduplicate_classes()` handles three strategies: identical merge (compatible fields → merge), variant split (conflicting classes with `source_context` → distinct classes + union alias), and widening merge (conflicting without context → union field types). Check `_deduplicate_classes()`, `_merge_class_fields()`, `_widen_class_fields()`.

### "Schema fetch fails"
`SchemaFetcher` has a 30-second timeout on `urlopen()`. HTTP errors produce "Schema not found (HTTP {code})" and network errors produce "Network error... {reason}" — check the exception type to distinguish "schema doesn't exist" from "server unreachable".

### "Quantity type not generated"
The `allOf[tQuantityValue, unit_ref]` pattern must be recognized by `_resolve_all_of_property()`. If the unit ref points to a missing unit in the units schema, the type won't generate. Check the units.schema.json has the required unit definition.

### "Empty generated model file"
Tabular schemas (e.g., `mass-spectrometry.tabular.schema`) use flat `properties` without allOf+hierarchy composition. The codegen doesn't handle these — they produce empty output. These schemas are not supported.
