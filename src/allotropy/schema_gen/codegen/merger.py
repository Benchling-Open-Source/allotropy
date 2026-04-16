"""Schema merging utilities for anyOf/oneOf/allOf composition.

Pure functions and the SchemaMerger class that handles merging properties
from variant sub-schemas. Independent of code generation — operates on
raw JSON Schema dicts.
"""

from __future__ import annotations

from typing import Any
import warnings

from allotropy.schema_gen.naming import parse_ref


def ref_base_url(ref: str) -> str:
    """Extract the schema URL from a $ref string, stripping any fragment."""
    return ref.split("#")[0]


def merge_props_into(
    target: dict[str, Any],
    source: dict[str, Any],
    *,
    any_of: bool = False,
) -> None:
    """Deep-merge *source* properties into *target*, merging on conflict."""
    for pk, pv in source.items():
        if pk in target:
            target[pk] = deep_merge_schemas(target[pk], pv, any_of=any_of)
        else:
            target[pk] = pv


def strip_required_recursive(schema: Any) -> Any:
    """Recursively remove all ``required`` arrays from a schema.

    Used after merging anyOf variants: in a union type, no individual
    variant's fields should be strictly required in the merged result,
    since only one variant applies at runtime.
    """
    if isinstance(schema, dict):
        return {
            k: strip_required_recursive(v) for k, v in schema.items() if k != "required"
        }
    if isinstance(schema, list):
        return [strip_required_recursive(item) for item in schema]
    return schema


def absolutize_refs(schema: Any, base_url: str) -> Any:
    """Rewrite local ``#/$defs/...`` refs to absolute URLs.

    When properties from one schema file are deep-merged into a different
    schema's context, local refs become dangling.  This function rewrites
    them to ``{base_url}#/$defs/...`` so they resolve correctly.
    """
    if isinstance(schema, dict):
        result: dict[str, Any] = {}
        for key, value in schema.items():
            if key == "$ref" and isinstance(value, str) and value.startswith("#/"):
                result[key] = f"{base_url}{value}"
            else:
                result[key] = absolutize_refs(value, base_url)
        return result
    if isinstance(schema, list):
        return [absolutize_refs(item, base_url) for item in schema]
    return schema


def deep_merge_schemas(
    base: dict[str, Any],
    overlay: dict[str, Any],
    *,
    any_of: bool = False,
) -> dict[str, Any]:
    """Deep-merge two JSON schemas, with *overlay* taking precedence.

    Recursively merges ``properties`` dicts and ``items`` sub-schemas so that
    a technique schema overlay inherits all nested structure from the base
    hierarchy schema while adding or replacing its own fields.

    When *any_of* is True (merging anyOf variants), ``required`` arrays are
    intersected rather than unioned — a field is only required in the merged
    result if both variants require it.
    """
    result = dict(base)

    for key, value in overlay.items():
        if key == "properties" and "properties" in result:
            merged = dict(result["properties"])
            for pname, pschema in value.items():
                if (
                    pname in merged
                    and isinstance(merged[pname], dict)
                    and isinstance(pschema, dict)
                ):
                    merged[pname] = deep_merge_schemas(
                        merged[pname], pschema, any_of=any_of
                    )
                else:
                    merged[pname] = pschema
            result["properties"] = merged
        elif key == "required":
            if "required" in result:
                if any_of:
                    result["required"] = list(set(result["required"]) & set(value))
                else:
                    result["required"] = list(set(result["required"]) | set(value))
            elif any_of:
                # anyOf: overlay has required but base doesn't →
                # intersection with ∅ = ∅, so don't add.
                pass
            else:
                result[key] = value
        elif key == "items" and "items" in result:
            if isinstance(result["items"], dict) and isinstance(value, dict):
                result["items"] = deep_merge_schemas(
                    result["items"], value, any_of=any_of
                )
            else:
                result[key] = value
        elif key == "allOf" and "allOf" in result:
            if any_of:
                # In anyOf mode, merge inline allOf items with anyOf semantics
                # so that nested required fields get intersected rather than
                # accumulated.  $ref items are deduplicated.
                refs: set[str] = set()
                inline_items: list[dict[str, Any]] = []
                for item in result["allOf"] + value:
                    if "$ref" in item and len(item) == 1:
                        refs.add(item["$ref"])
                    elif isinstance(item, dict):
                        inline_items.append(item)
                merged_inline: dict[str, Any] = {}
                for item in inline_items:
                    if merged_inline:
                        merged_inline = deep_merge_schemas(
                            merged_inline, item, any_of=True
                        )
                    else:
                        merged_inline = dict(item)
                result_allof: list[dict[str, Any]] = [{"$ref": r} for r in refs]
                if merged_inline:
                    result_allof.append(merged_inline)
                result["allOf"] = result_allof
            else:
                result["allOf"] = result["allOf"] + value
        else:
            result[key] = value

    # In anyOf mode: if the base had "required" but the overlay didn't
    # define any, the intersection with ∅ is ∅.
    if any_of and "required" in result and "required" not in overlay:
        result["required"] = []

    return result


# ---------------------------------------------------------------------------
# SchemaMerger
# ---------------------------------------------------------------------------


class SchemaMerger:
    """Merges properties from variant sub-schemas (anyOf/oneOf composition).

    Extracted from SchemaCodeGenerator so the merge logic can be tested
    and reasoned about independently of code generation.
    """

    def __init__(self, schemas: dict[str, dict[str, Any]]) -> None:
        self.schemas = schemas

    def resolve_ref_to_schema(
        self, current_schema_url: str, ref: str
    ) -> dict[str, Any] | None:
        """Resolve a $ref string to its actual JSON Schema definition dict."""
        ref_schema_url, def_name = parse_ref(ref)

        if ref_schema_url is None:
            schema = self.schemas.get(current_schema_url, {})
            if def_name:
                defs: dict[str, Any] = schema.get("$defs", {})
                return defs.get(def_name)
            return None

        schema = self.schemas.get(ref_schema_url, {})
        if def_name:
            defs = schema.get("$defs", {})
            return defs.get(def_name)
        return schema

    def deep_merge_base_ref_properties(
        self,
        schema_url: str,
        base_refs: list[str],
        merged_props: dict[str, Any],
    ) -> None:
        """Deep-merge overlapping properties from base $ref schemas into merged_props.

        When a technique schema extends a base (e.g., techniqueAggregateDocument)
        and redefines a nested property (e.g., "device system document"), the
        base's full schema must be merged in so that inline types include all
        hierarchy-level fields plus technique-specific additions.
        """
        for ref in base_refs:
            ref_base_url_str = ref_base_url(ref)
            base_schema = self.resolve_ref_to_schema(schema_url, ref)
            if base_schema and "properties" in base_schema:
                base_props = base_schema["properties"]
                if ref_base_url_str:
                    base_props = {
                        k: absolutize_refs(v, ref_base_url_str)
                        for k, v in base_props.items()
                    }
                for prop_key in list(merged_props.keys()):
                    if prop_key in base_props:
                        merged_props[prop_key] = deep_merge_schemas(
                            base_props[prop_key], merged_props[prop_key]
                        )

    def _resolve_variant(
        self,
        schema_url: str,
        variant: dict[str, Any],
        fallback_base_url: str = "",
    ) -> tuple[dict[str, Any] | None, str]:
        """Resolve a variant dict to (schema, base_url).

        Returns (None, "") if the variant cannot be resolved.
        """
        if "$ref" in variant:
            base_url = ref_base_url(variant["$ref"]) or fallback_base_url
            return self.resolve_ref_to_schema(schema_url, variant["$ref"]), base_url
        if isinstance(variant, dict):
            return variant, fallback_base_url
        return None, ""

    @staticmethod
    def _merge_variant_props(
        variant_schema: dict[str, Any],
        base_url: str,
        merged_props: dict[str, Any],
    ) -> None:
        """Absolutize and merge a resolved variant's properties into *merged_props*."""
        if "properties" not in variant_schema:
            return
        props = variant_schema["properties"]
        if base_url:
            props = {k: absolutize_refs(v, base_url) for k, v in props.items()}
        merge_props_into(merged_props, props)

    def merge_variant_properties(
        self,
        schema_url: str,
        variants: list[dict[str, Any]],
        merged_props: dict[str, Any],
    ) -> None:
        """Merge properties from anyOf/oneOf variant sub-schemas.

        Resolves each variant's ``$ref`` to its schema definition and
        deep-merges its properties into *merged_props*.  Also recurses
        one level into nested anyOf/oneOf within each variant (e.g.,
        detector sub-schemas that have oneOf for data cube types).
        """
        for variant in variants:
            variant_schema, variant_base_url = self._resolve_variant(
                schema_url, variant
            )
            if not variant_schema:
                continue
            self._merge_variant_props(variant_schema, variant_base_url, merged_props)
            # Recurse one level into nested anyOf/oneOf within the variant
            # (e.g., a detector sub-schema has oneOf for different data cubes).
            # Only one level is supported — deeper nesting raises a warning.
            for nested_key in ("anyOf", "oneOf"):
                if nested_key not in variant_schema:
                    continue
                for nested in variant_schema[nested_key]:
                    nested_schema, nested_base_url = self._resolve_variant(
                        schema_url, nested, fallback_base_url=variant_base_url
                    )
                    if nested_schema:
                        self._merge_variant_props(
                            nested_schema, nested_base_url, merged_props
                        )
                        self._warn_deep_nesting(nested_schema, nested_key, schema_url)

    @staticmethod
    def _warn_deep_nesting(
        schema: dict[str, Any], parent_key: str, schema_url: str
    ) -> None:
        """Warn if a nested schema has further anyOf/oneOf (3+ levels)."""
        for deeper_key in ("anyOf", "oneOf"):
            if deeper_key in schema:
                warnings.warn(
                    f"Schema {schema_url} has 3+ levels of "
                    f"anyOf/oneOf nesting ({deeper_key} inside "
                    f"{parent_key}). Properties from the "
                    f"innermost level are not merged.",
                    stacklevel=3,
                )

    def merge_any_of_variants_into_props(
        self,
        schema_url: str,
        any_of_variants: list[dict[str, Any]],
        merged_props: dict[str, Any],
    ) -> None:
        """Merge anyOf variant schemas into merged_props as optional fields.

        Resolves each variant's ``$ref``, deep-merges all variants together
        with ``any_of=True`` (intersecting required arrays), strips all
        ``required`` from the result, and folds the resulting properties
        into *merged_props*.  Also collects nested ``oneOf`` variants from
        each resolved schema and merges those properties too.

        This handles the multi-detector pattern where anyOf variants each
        contribute different measurement fields to a common item type.
        """
        any_of_merged: dict[str, Any] | None = None
        # Collect all oneOf variants from all detector schemas before
        # deep-merge (which overwrites oneOf with the last value).
        all_one_of_variants: list[dict[str, Any]] = []

        for variant in any_of_variants:
            if "$ref" in variant:
                ref_schema_url, ref_def = parse_ref(variant["$ref"])
                if ref_def:
                    if ref_schema_url:
                        ref_schema = self.schemas.get(ref_schema_url, {})
                    else:
                        ref_schema = self.schemas.get(schema_url, {})
                    ref_def_schema = ref_schema.get("$defs", {}).get(ref_def, {})
                    # Collect oneOf variants before deep-merge
                    abs_base = ref_schema_url or schema_url
                    if "oneOf" in ref_def_schema:
                        for one_of_v in ref_def_schema["oneOf"]:
                            all_one_of_variants.append(
                                absolutize_refs(one_of_v, abs_base)
                            )
                    if any_of_merged is None:
                        any_of_merged = dict(ref_def_schema)
                    else:
                        any_of_merged = deep_merge_schemas(
                            any_of_merged, ref_def_schema, any_of=True
                        )
            elif isinstance(variant, dict) and "properties" in variant:
                if any_of_merged is None:
                    any_of_merged = dict(variant)
                else:
                    any_of_merged = deep_merge_schemas(
                        any_of_merged, variant, any_of=True
                    )

        if any_of_merged:
            # Strip all required arrays: in a union, no variant's fields
            # should be strictly required since only one variant applies.
            any_of_stripped: dict[str, Any] = strip_required_recursive(any_of_merged)
            if "properties" in any_of_stripped:
                merge_props_into(
                    merged_props, any_of_stripped["properties"], any_of=True
                )

        # Extract properties from oneOf variants as optional fields
        for one_of_v in all_one_of_variants:
            if isinstance(one_of_v, dict) and "properties" in one_of_v:
                merge_props_into(merged_props, one_of_v["properties"], any_of=True)


# ---------------------------------------------------------------------------
# allOf partitioning helpers
# ---------------------------------------------------------------------------


def partition_all_of(
    all_of: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    """Split allOf items into $ref strings and inline schema dicts."""
    refs: list[str] = []
    schemas: list[dict[str, Any]] = []
    for item in all_of:
        if "$ref" in item:
            refs.append(item["$ref"])
        elif isinstance(item, dict):
            schemas.append(item)
    return refs, schemas


def collect_all_of_parts(
    parent_schema: dict[str, Any],
    all_of: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Collect properties, required fields, and base $refs from a schema + allOf.

    Collects direct properties and $refs.  Does NOT handle anyOf/oneOf
    variant merging — callers handle that based on context.
    """
    merged_props: dict[str, Any] = {}
    merged_required: list[str] = []
    base_refs: list[str] = []

    if "properties" in parent_schema:
        merge_props_into(merged_props, parent_schema["properties"])
    if "required" in parent_schema:
        merged_required.extend(parent_schema["required"])

    for item in all_of:
        if "$ref" in item:
            base_refs.append(item["$ref"])
        if isinstance(item, dict):
            if "properties" in item:
                merge_props_into(merged_props, item["properties"])
            if "required" in item:
                merged_required.extend(item["required"])

    return merged_props, merged_required, base_refs
