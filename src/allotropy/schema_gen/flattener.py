"""Pre-processing: flatten external $ref#/$defs/X into local $defs.

datamodel-codegen v0.25.2 crashes on allOf with external $ref#/$defs/X patterns.
This module resolves those references by copying the referenced definitions into
the schema's own $defs and rewriting the refs to be local.
"""

from __future__ import annotations

import copy
import urllib.parse
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

    Iterates until no new external refs or missing local refs remain.
    Both external ref rewriting and transitive local ref copying are
    interleaved in the same loop so that defs brought in by transitive
    copying also get their external refs rewritten.
    """
    result = copy.deepcopy(schema)
    if "$defs" not in result:
        result["$defs"] = {}

    local_defs = result["$defs"]
    processed_objs: set[int] = set()

    for _ in range(50):  # safety limit
        # Step 1: find and rewrite external $defs refs
        refs_found: list[tuple[dict[str, Any], str]] = []
        _collect_external_def_refs(result, refs_found)

        new_refs = [
            (obj, ref) for obj, ref in refs_found if id(obj) not in processed_objs
        ]

        for obj, ref in new_refs:
            processed_objs.add(id(obj))
            schema_url, def_name = _parse_def_ref(ref)
            if schema_url is None or def_name is None:
                continue

            # Copy or merge the definition
            source_schema = all_schemas.get(schema_url, {})
            source_defs = source_schema.get("$defs", {})
            if def_name in source_defs:
                if def_name not in local_defs:
                    local_defs[def_name] = copy.deepcopy(source_defs[def_name])
                else:
                    # Merge when different source schemas define the same $defs name
                    # (e.g., anyOf branches referencing detector vs fluorescence variants).
                    # Use intersect semantics for "required": only keep fields required
                    # in ALL source variants (anyOf means any branch may apply).
                    _anyof_merge_def(
                        local_defs[def_name],
                        source_defs[def_name],
                        local_defs,
                    )

            # Rewrite the ref to be local
            obj["$ref"] = f"#/$defs/{def_name}"

        # Step 2: copy transitive local refs (defs referenced via
        # #/$defs/X inside copied defs where X is not yet in local $defs)
        missing: list[str] = []
        _collect_missing_local_refs(local_defs, local_defs, missing)

        for def_name in missing:
            for source_schema in all_schemas.values():
                source_defs = source_schema.get("$defs", {})
                if def_name in source_defs:
                    local_defs[def_name] = copy.deepcopy(source_defs[def_name])
                    break

        # Stop when neither step found anything new
        if not new_refs and not missing:
            break

    return result


def strip_asm_keys(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove $asm.* metadata keys that datamodel-codegen doesn't understand."""
    result: dict[str, Any] = _strip_keys_recursive(copy.deepcopy(schema))
    return result


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
    # URL-decode percent-encoded characters (e.g., %23 → #)
    def_name = urllib.parse.unquote(def_name)
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


def _copy_transitive_local_refs(
    local_defs: dict[str, Any],
    all_schemas: dict[str, dict[str, Any]],
) -> None:
    """Copy definitions referenced by local #/$defs/X refs that are missing.

    When flatten_external_defs copies a definition like ``techniqueDocument``
    from hierarchy.schema, that definition may contain internal ``#/$defs/X``
    refs to other definitions in the hierarchy schema (e.g.
    ``processedDataAggregateDocument``). These refs become dangling unless
    we also copy the referenced definitions.
    """
    for _ in range(50):  # safety limit
        missing: list[str] = []
        _collect_missing_local_refs(local_defs, local_defs, missing)
        if not missing:
            break
        for def_name in missing:
            for source_schema in all_schemas.values():
                source_defs = source_schema.get("$defs", {})
                if def_name in source_defs:
                    local_defs[def_name] = copy.deepcopy(source_defs[def_name])
                    break


def _collect_missing_local_refs(
    obj: Any, local_defs: dict[str, Any], missing: list[str]
) -> None:
    """Find #/$defs/X refs where X is not in local_defs."""
    if isinstance(obj, dict):
        if "$ref" in obj:
            ref = obj["$ref"]
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                def_name = ref[len("#/$defs/") :]
                if def_name not in local_defs and def_name not in missing:
                    missing.append(def_name)
        for value in obj.values():
            _collect_missing_local_refs(value, local_defs, missing)
    elif isinstance(obj, list):
        for item in obj:
            _collect_missing_local_refs(item, local_defs, missing)


def remove_unreferenced_defs(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove $defs entries that are not referenced anywhere in the schema.

    After merge_allof_overlays, some $defs (like techniqueDocument) are
    fully inlined and no longer referenced. Removing them prevents
    datamodel-codegen from generating shadowing base-only classes.
    """
    result = copy.deepcopy(schema)
    local_defs = result.get("$defs", {})
    if not local_defs:
        return result

    for _ in range(10):  # iterate: removing a def may make others unreferenced
        referenced: set[str] = set()
        _collect_all_def_refs(result, local_defs, referenced)
        unreferenced = [name for name in local_defs if name not in referenced]
        if not unreferenced:
            break
        for name in unreferenced:
            del local_defs[name]

    return result


def _collect_all_def_refs(
    obj: Any, local_defs: dict[str, Any], referenced: set[str]
) -> None:
    """Collect all $defs names referenced via #/$defs/X in the schema."""
    if isinstance(obj, dict):
        if "$ref" in obj:
            ref = obj["$ref"]
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                referenced.add(ref[len("#/$defs/") :])
        for key, value in obj.items():
            if key == "$defs":
                # Recurse INTO $defs values to find cross-references
                for def_schema in value.values():
                    _collect_all_def_refs(def_schema, local_defs, referenced)
            else:
                _collect_all_def_refs(value, local_defs, referenced)
    elif isinstance(obj, list):
        for item in obj:
            _collect_all_def_refs(item, local_defs, referenced)


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
    """Remove $asm.* metadata keys from a schema tree.

    Preserves ``$asm.manifest`` — it is a real schema property (not metadata)
    that maps to the ``field_asm_manifest`` field on the generated Model class.
    """
    if isinstance(obj, dict):
        return {
            k: _strip_keys_recursive(v)
            for k, v in obj.items()
            if not k.startswith("$asm.") or k == "$asm.manifest"
        }
    if isinstance(obj, list):
        return [_strip_keys_recursive(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# allOf overlay merging
# ---------------------------------------------------------------------------


def merge_allof_overlays(schema: dict[str, Any]) -> dict[str, Any]:
    """Merge allOf branches that combine a $ref with a properties overlay.

    Allotrope schemas use allOf to compose base hierarchy types (via $ref)
    with technique-specific property overlays. datamodel-codegen generates
    separate numbered classes for each allOf branch instead of merging them.

    This pre-processing step resolves the $ref, deep-merges the overlay
    properties into the base, and replaces the allOf with a single
    self-contained schema so datamodel-codegen produces complete classes.

    Must be called AFTER flatten_external_defs (so $refs are local).
    """
    result = copy.deepcopy(schema)
    _unwrap_single_allof(result)
    local_defs = result.get("$defs", {})
    _merge_allofs_recursive(result, local_defs)
    _resolve_degenerate_anyof(result, local_defs)
    # Run unwrap again: earlier passes may leave single-branch allOfs behind
    # (e.g., Case 3 merges property overlays, leaving allOf:[{anyOf resolved}]).
    _unwrap_single_allof(result)
    return result


def _deep_update(base: dict[str, Any], overlay: dict[str, Any]) -> None:
    """Recursively merge overlay dict into base dict, preserving nested structure.

    Unlike ``dict.update()``, when both base and overlay have the same key
    pointing to dicts, the dicts are merged recursively rather than replaced.
    ``required`` arrays are merged (deduplicated union).
    """
    for k, v in overlay.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_update(base[k], v)
        elif k == "required" and isinstance(base.get(k), list) and isinstance(v, list):
            base[k] = list(dict.fromkeys(base[k] + v))
        else:
            base[k] = v


def _unwrap_single_allof(obj: Any) -> None:
    """Recursively unwrap allOf arrays with a single element.

    ``{"allOf": [X]}`` → ``X`` merged into the parent object.
    Runs in a loop to handle nested single-element wrapping.
    """
    if not isinstance(obj, dict):
        return

    while "allOf" in obj and isinstance(obj["allOf"], list) and len(obj["allOf"]) == 1:
        branch = obj["allOf"][0]
        if not isinstance(branch, dict):
            break
        del obj["allOf"]
        for k, v in branch.items():
            if k not in obj:
                obj[k] = v
            elif k == "properties" and isinstance(obj.get(k), dict):
                _deep_update(obj[k], v)
            elif k == "required":
                obj[k] = list(dict.fromkeys(obj.get(k, []) + v))

    for value in list(obj.values()):
        if isinstance(value, dict):
            _unwrap_single_allof(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _unwrap_single_allof(item)


def _resolve_degenerate_anyof(obj: Any, local_defs: dict[str, Any]) -> None:
    """Resolve anyOf where all branches point to the same $ref.

    When anyOf has multiple items but they all resolve to the same local $ref,
    the anyOf is degenerate — just resolve the ref and merge into the parent.
    This happens after flatten_external_defs merges detector + fluorescence
    variants into a single measurementDocumentItems def.
    """
    if not isinstance(obj, dict):
        return

    if "anyOf" in obj and isinstance(obj["anyOf"], list):
        anyof = obj["anyOf"]
        refs = set()
        for branch in anyof:
            if isinstance(branch, dict) and "$ref" in branch and len(branch) == 1:
                refs.add(branch["$ref"])
            else:
                refs = set()  # Not all pure refs
                break
        if len(refs) == 1:
            ref = refs.pop()
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                def_name = ref[len("#/$defs/"):]
                if def_name in local_defs:
                    resolved = copy.deepcopy(local_defs[def_name])
                    del obj["anyOf"]
                    _deep_merge_schema(obj, resolved, local_defs)

    for value in list(obj.values()):
        if isinstance(value, dict):
            _resolve_degenerate_anyof(value, local_defs)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _resolve_degenerate_anyof(item, local_defs)


def _merge_allofs_recursive(obj: Any, local_defs: dict[str, Any]) -> None:
    """Walk schema tree and merge allOf patterns with local $ref + overlay."""
    if not isinstance(obj, dict):
        return

    if "allOf" in obj and isinstance(obj["allOf"], list):
        allof = obj["allOf"]

        # Classify branches
        ref_indices: list[int] = []
        prop_indices: list[int] = []

        for i, branch in enumerate(allof):
            if not isinstance(branch, dict):
                continue
            if (
                "$ref" in branch
                and isinstance(branch["$ref"], str)
                and branch["$ref"].startswith("#/$defs/")
                and len(branch) == 1
            ):
                ref_indices.append(i)
            elif "properties" in branch or "required" in branch:
                prop_indices.append(i)

        merged = False

        # Case 1: Single $ref + property overlays (original pattern)
        if len(ref_indices) == 1 and prop_indices:
            ref_idx = ref_indices[0]
            ref_str = allof[ref_idx]["$ref"]
            def_name = ref_str[len("#/$defs/") :]

            if def_name in local_defs:
                resolved = copy.deepcopy(local_defs[def_name])

                for pi in prop_indices:
                    _deep_merge_schema(resolved, allof[pi], local_defs)

                remaining = [
                    allof[i]
                    for i in range(len(allof))
                    if i != ref_idx and i not in prop_indices
                ]

                del obj["allOf"]
                for k, v in resolved.items():
                    if k == "properties" and "properties" in obj:
                        _deep_merge_props(obj["properties"], v, local_defs)
                    elif k == "required" and "required" in obj:
                        obj["required"] = list(
                            dict.fromkeys(obj.get("required", []) + v)
                        )
                    else:
                        obj[k] = v

                if remaining:
                    obj["allOf"] = remaining
                merged = True

        # Case 2: Multiple pure $ref branches (composition pattern)
        # e.g., allOf: [{$ref: tDimensionData}, {$ref: tMeasureData}]
        if not merged and len(ref_indices) >= 2 and not prop_indices:
            all_resolvable = True
            for ri in ref_indices:
                def_name = allof[ri]["$ref"][len("#/$defs/") :]
                if def_name not in local_defs:
                    all_resolvable = False
                    break

            if all_resolvable:
                # Start with the first ref, merge subsequent ones in
                first_def = allof[ref_indices[0]]["$ref"][len("#/$defs/") :]
                resolved = copy.deepcopy(local_defs[first_def])

                for ri in ref_indices[1:]:
                    other_def = allof[ri]["$ref"][len("#/$defs/") :]
                    _deep_merge_schema(resolved, local_defs[other_def], local_defs)

                remaining = [
                    allof[i] for i in range(len(allof)) if i not in ref_indices
                ]

                del obj["allOf"]
                for k, v in resolved.items():
                    if k == "properties" and "properties" in obj:
                        _deep_merge_props(obj["properties"], v, local_defs)
                    elif k == "required" and "required" in obj:
                        obj["required"] = list(
                            dict.fromkeys(obj.get("required", []) + v)
                        )
                    else:
                        obj[k] = v

                if remaining:
                    obj["allOf"] = remaining

        # Case 3: Property overlays only (no $ref) with non-property branches
        # e.g., allOf: [{properties: {...}, required: [...]}, {anyOf: [...]}]
        # Merge property overlays into parent, keep other branches.
        if not merged and not ref_indices and prop_indices:
            for pi in prop_indices:
                _deep_merge_schema(obj, allof[pi], local_defs)

            remaining = [
                allof[i] for i in range(len(allof)) if i not in prop_indices
            ]

            del obj["allOf"]
            if remaining:
                obj["allOf"] = remaining

    # Recurse into all values
    for value in list(obj.values()):
        if isinstance(value, dict):
            _merge_allofs_recursive(value, local_defs)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _merge_allofs_recursive(item, local_defs)


def _deep_merge_schema(
    base: dict[str, Any], overlay: dict[str, Any], local_defs: dict[str, Any]
) -> None:
    """Deep merge overlay schema into base schema in-place."""
    # Resolve $ref in base if present (e.g. processedDataAggregateDocument)
    if (
        "$ref" in base
        and isinstance(base["$ref"], str)
        and base["$ref"].startswith("#/$defs/")
    ):
        def_name = base["$ref"][len("#/$defs/") :]
        if def_name in local_defs:
            resolved = copy.deepcopy(local_defs[def_name])
            del base["$ref"]
            base.update(resolved)

    for key, value in overlay.items():
        if key.startswith("$asm."):
            continue

        if key == "properties":
            if "properties" not in base:
                base["properties"] = {}
            _deep_merge_props(base["properties"], value, local_defs)
        elif key == "required":
            base_req = base.get("required", [])
            base["required"] = list(dict.fromkeys(base_req + value))
        elif key == "items" and isinstance(value, dict):
            if "items" in base and isinstance(base["items"], dict):
                _deep_merge_schema(base["items"], value, local_defs)
            else:
                base["items"] = copy.deepcopy(value)
        elif key == "allOf" and isinstance(value, list):
            if "allOf" in base and isinstance(base["allOf"], list):
                _merge_allof_arrays(base["allOf"], value, local_defs)
            else:
                base["allOf"] = copy.deepcopy(value)
        elif key not in base:
            base[key] = copy.deepcopy(value)


def _anyof_merge_def(
    base: dict[str, Any], overlay: dict[str, Any], local_defs: dict[str, Any]
) -> None:
    """Merge an anyOf variant def into base, intersecting required arrays.

    Like _deep_merge_schema but handles 'required' with intersection semantics:
    only fields required in ALL variants stay required. This is correct for
    anyOf where each branch independently specifies its own requirements.
    """
    # Snapshot all required arrays in the base before merging
    base_required_map: dict[str, set[str]] = {}
    _collect_required_by_path(base, "", base_required_map)

    # Snapshot overlay required arrays
    overlay_required_map: dict[str, set[str]] = {}
    _collect_required_by_path(overlay, "", overlay_required_map)

    # Merge properties/structure as normal
    _deep_merge_schema(base, overlay, local_defs)

    # Now fix up required arrays: intersect at every path
    _intersect_required_by_path(base, "", base_required_map, overlay_required_map)


def _collect_required_by_path(
    obj: Any, path: str, result: dict[str, set[str]]
) -> None:
    """Walk a schema and collect required arrays keyed by dotted path."""
    if not isinstance(obj, dict):
        return
    if "required" in obj and isinstance(obj["required"], list):
        result[path] = set(obj["required"])
    for key, value in obj.items():
        if key == "required":
            continue
        child_path = f"{path}.{key}" if path else key
        if isinstance(value, dict):
            _collect_required_by_path(value, child_path, result)


def _intersect_required_by_path(
    obj: Any,
    path: str,
    base_map: dict[str, set[str]],
    overlay_map: dict[str, set[str]],
) -> None:
    """Walk merged schema and intersect required arrays at paths seen in both maps."""
    if not isinstance(obj, dict):
        return
    if "required" in obj and isinstance(obj["required"], list):
        base_req = base_map.get(path, set())
        overlay_req = overlay_map.get(path, set())
        if base_req and overlay_req:
            obj["required"] = list(base_req & overlay_req)
        elif path in base_map or path in overlay_map:
            # One branch had required, the other didn't → nothing is universally required
            obj.pop("required", None)
    for key, value in obj.items():
        if key == "required":
            continue
        child_path = f"{path}.{key}" if path else key
        if isinstance(value, dict):
            _intersect_required_by_path(value, child_path, base_map, overlay_map)


def _deep_merge_props(
    base_props: dict[str, Any],
    overlay_props: dict[str, Any],
    local_defs: dict[str, Any],
) -> None:
    """Deep merge overlay properties into base properties."""
    for prop_name, prop_schema in overlay_props.items():
        if prop_name not in base_props:
            base_props[prop_name] = copy.deepcopy(prop_schema)
        elif isinstance(prop_schema, dict) and isinstance(base_props[prop_name], dict):
            _deep_merge_schema(base_props[prop_name], prop_schema, local_defs)
        else:
            base_props[prop_name] = copy.deepcopy(prop_schema)


def _merge_allof_arrays(
    base_allof: list[Any],
    overlay_allof: list[Any],
    local_defs: dict[str, Any],
) -> None:
    """Merge overlay allOf branches into base allOf branches."""
    for overlay_branch in overlay_allof:
        if not isinstance(overlay_branch, dict):
            continue
        if "properties" in overlay_branch or "required" in overlay_branch:
            # Find a base branch with properties to merge into
            merged = False
            for base_branch in base_allof:
                if isinstance(base_branch, dict) and (
                    "properties" in base_branch or "required" in base_branch
                ):
                    _deep_merge_schema(base_branch, overlay_branch, local_defs)
                    merged = True
                    break
            if not merged:
                base_allof.append(copy.deepcopy(overlay_branch))
        elif "$ref" in overlay_branch:
            ref = overlay_branch["$ref"]
            if not any(
                isinstance(b, dict) and b.get("$ref") == ref for b in base_allof
            ):
                base_allof.append(copy.deepcopy(overlay_branch))
