# BENCHLING Units Schema

This schema defines unit types used by BENCHLING technique schemas that reference
`tQuantityValue` and `tNullableQuantityValue` with specific unit constraints.

These unit definitions were previously embedded as `$custom` references in BENCHLING
technique schemas and resolved at validation time. They are now explicit schema
definitions so that the code generator can resolve them to typed quantity value classes.

## Unit definitions

All unit `$defs` entries follow the same structure:
```json
{
  "properties": { "unit": { "type": "string", "const": "<unit>" } },
  "required": ["unit"]
}
```

Each entry constrains the `unit` field to a specific constant value (e.g., `"(unitless)"`,
`"%"`, `"nm"`, etc.).
