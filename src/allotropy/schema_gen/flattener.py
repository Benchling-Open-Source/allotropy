"""Pre-processing: flatten external $ref#/$defs/X into local $defs.

datamodel-codegen v0.25.2 crashes on allOf with external $ref#/$defs/X patterns.
This module resolves those references by copying the referenced definitions into
the schema's own $defs and rewriting the refs to be local.
"""

from __future__ import annotations

import copy
from typing import Any

from allotropy.schema_gen.naming import normalize_schema_url


def flatten_external_defs(
    schema: dict[str, Any],
    all_schemas: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Create a self-contained schema by inlining external $defs references.

    External refs of the form ``url#/$defs/name`` are resolved by copying the
    referenced definition into the schema's own ``$defs`` and rewriting the
    ``$ref`` to ``#/$defs/name``. Whole-file refs (no ``#/$defs/``) are left
    untouched since datamodel-codegen handles those.

    Iterates until no external ``$defs`` refs remain (handles transitive deps).
    """
    result = copy.deepcopy(schema)
    if "$defs" not in result:
        result["$defs"] = {}

    local_defs = result["$defs"]
    seen_refs: set[str] = set()

    for _ in range(50):  # safety limit
        refs_found: list[tuple[dict[str, Any], str]] = []
        _collect_external_def_refs(result, refs_found)

        new_refs = [(obj, ref) for obj, ref in refs_found if ref not in seen_refs]
        if not new_refs:
            break

        for obj, ref in new_refs:
            seen_refs.add(ref)
            schema_url, def_name = _parse_def_ref(ref)
            if schema_url is None or def_name is None:
                continue

            # Copy the definition if we haven't already
            if def_name not in local_defs:
                source_schema = all_schemas.get(schema_url, {})
                source_defs = source_schema.get("$defs", {})
                if def_name in source_defs:
                    local_defs[def_name] = copy.deepcopy(source_defs[def_name])

            # Rewrite the ref to be local
            obj["$ref"] = f"#/$defs/{def_name}"

    return result


def strip_asm_keys(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove $asm.* metadata keys that datamodel-codegen doesn't understand."""
    return _strip_keys_recursive(copy.deepcopy(schema))


def needs_flattening(schema: dict[str, Any]) -> bool:
    """Check if a schema has external $ref#/$defs/X patterns."""
    refs: list[tuple[dict[str, Any], str]] = []
    _collect_external_def_refs(schema, refs)
    return len(refs) > 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_def_ref(ref: str) -> tuple[str | None, str | None]:
    """Parse an external $ref with $defs fragment into (canonical_url, def_name).

    Returns (None, None) if the ref doesn't match the pattern.
    """
    if "#" not in ref:
        return None, None

    schema_part, fragment = ref.split("#", 1)
    if not schema_part or not fragment.startswith("/$defs/"):
        return None, None

    def_name = fragment[len("/$defs/") :]
    # Decode JSON Pointer escapes
    def_name = def_name.replace("~1", "/").replace("~0", "~")

    try:
        canonical = normalize_schema_url(schema_part)
    except ValueError:
        return None, None

    return canonical, def_name


def _collect_external_def_refs(
    obj: Any, refs: list[tuple[dict[str, Any], str]]
) -> None:
    """Walk schema tree and collect (containing_dict, ref_string) for external $defs refs."""
    if isinstance(obj, dict):
        if "$ref" in obj:
            ref = obj["$ref"]
            if not ref.startswith("#") and "#/$defs/" in ref:
                refs.append((obj, ref))
        for value in obj.values():
            _collect_external_def_refs(value, refs)
    elif isinstance(obj, list):
        for item in obj:
            _collect_external_def_refs(item, refs)


def strip_external_whole_schema_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Replace remaining whole-schema external $ref URLs with opaque types.

    After flatten_external_defs resolves $defs refs, there may still be
    whole-schema refs (e.g., manifest.schema) that datamodel-codegen can't
    resolve without HTTP. Replace these with ``{"type": "object"}`` so
    generation doesn't crash.
    """
    result = copy.deepcopy(schema)
    _neutralize_external_refs(result)
    return result


def _neutralize_external_refs(obj: Any) -> None:
    """In-place: replace external $ref URLs with {"type": "string"}."""
    if isinstance(obj, dict):
        if "$ref" in obj and not obj["$ref"].startswith("#"):
            # Replace the external ref with a simple type
            obj.pop("$ref")
            obj["type"] = "string"
            return
        for value in obj.values():
            _neutralize_external_refs(value)
    elif isinstance(obj, list):
        for item in obj:
            _neutralize_external_refs(item)


def _strip_keys_recursive(obj: Any) -> Any:
    """Remove $asm.* keys and other metadata keys from a schema tree."""
    if isinstance(obj, dict):
        return {
            k: _strip_keys_recursive(v)
            for k, v in obj.items()
            if not k.startswith("$asm.")
        }
    if isinstance(obj, list):
        return [_strip_keys_recursive(item) for item in obj]
    return obj
