"""Unit tests for pure functions in allotropy.schema_gen.generate.

These test the BENCHLING forking / ref rewriting / unit collection logic
independently of schema fetching or file I/O.
"""

from __future__ import annotations

from typing import Any

from allotropy.schema_gen.generate import (
    _apply_ref_rewrite,
    _deep_merge,
    _extract_benchling_version,
    _extract_descriptive_name,
    _fork_benchling_shared_schemas,
    _has_url_keyed_defs,
    _rec_to_benchling_url,
    _rewrite_refs,
    _strip_embedded_defs,
)

BASE = "http://purl.allotrope.org/json-schemas/"
CORE_REC = f"{BASE}adm/core/REC/2024/09/core.schema"
HIERARCHY_REC = f"{BASE}adm/core/REC/2024/09/hierarchy.schema"
TECHNIQUE_BENCHLING = f"{BASE}adm/plate-reader/BENCHLING/2023/09/plate-reader.schema"


# ---------------------------------------------------------------------------
# _has_url_keyed_defs
# ---------------------------------------------------------------------------


class TestHasUrlKeyedDefs:
    def test_no_defs(self) -> None:
        assert _has_url_keyed_defs({}) is False

    def test_normal_defs(self) -> None:
        assert _has_url_keyed_defs({"$defs": {"myType": {}}}) is False

    def test_url_keyed_defs(self) -> None:
        assert _has_url_keyed_defs({"$defs": {"http://example.com/schema": {}}}) is True

    def test_https_keyed_defs(self) -> None:
        assert (
            _has_url_keyed_defs({"$defs": {"https://example.com/schema": {}}}) is True
        )

    def test_mixed_defs(self) -> None:
        schema: dict[str, Any] = {
            "$defs": {
                "normalType": {},
                "http://example.com/embedded": {},
            }
        }
        assert _has_url_keyed_defs(schema) is True


# ---------------------------------------------------------------------------
# _extract_benchling_version
# ---------------------------------------------------------------------------


class TestExtractBenchlingVersion:
    def test_benchling_url(self) -> None:
        url = f"{BASE}adm/plate-reader/BENCHLING/2023/09/plate-reader.schema"
        assert _extract_benchling_version(url) == "2023/09"

    def test_rec_url_returns_none(self) -> None:
        url = f"{BASE}adm/core/REC/2024/09/core.schema"
        assert _extract_benchling_version(url) is None

    def test_different_version(self) -> None:
        url = f"{BASE}adm/test/BENCHLING/2025/01/test.schema"
        assert _extract_benchling_version(url) == "2025/01"


# ---------------------------------------------------------------------------
# _rec_to_benchling_url
# ---------------------------------------------------------------------------


class TestRecToBenchlingUrl:
    def test_basic_conversion(self) -> None:
        result = _rec_to_benchling_url(CORE_REC, "2023/09")
        assert result == f"{BASE}adm/core/BENCHLING/2023/09/core.schema"

    def test_hierarchy_conversion(self) -> None:
        result = _rec_to_benchling_url(HIERARCHY_REC, "2023/09")
        assert result == f"{BASE}adm/core/BENCHLING/2023/09/hierarchy.schema"

    def test_preserves_filename(self) -> None:
        url = f"{BASE}adm/core/WD/2024/06/cube.schema"
        result = _rec_to_benchling_url(url, "2025/01")
        assert result.endswith("/cube.schema")
        assert "/BENCHLING/2025/01/" in result


# ---------------------------------------------------------------------------
# _apply_ref_rewrite
# ---------------------------------------------------------------------------


class TestApplyRefRewrite:
    def test_matching_prefix(self) -> None:
        rewrites = {CORE_REC: f"{BASE}adm/core/BENCHLING/2023/09/core.schema"}
        ref = f"{CORE_REC}#/$defs/myType"
        result = _apply_ref_rewrite(ref, rewrites)
        assert result == f"{BASE}adm/core/BENCHLING/2023/09/core.schema#/$defs/myType"

    def test_no_match_returns_unchanged(self) -> None:
        rewrites = {CORE_REC: f"{BASE}adm/core/BENCHLING/2023/09/core.schema"}
        ref = f"{HIERARCHY_REC}#/$defs/myType"
        result = _apply_ref_rewrite(ref, rewrites)
        assert result == ref

    def test_json_suffix_match(self) -> None:
        rewrites = {CORE_REC: f"{BASE}adm/core/BENCHLING/2023/09/core.schema"}
        ref = f"{CORE_REC}.json#/$defs/myType"
        result = _apply_ref_rewrite(ref, rewrites)
        assert ".json" in result  # suffix preserved in rewritten ref

    def test_empty_rewrites(self) -> None:
        ref = f"{CORE_REC}#/$defs/myType"
        assert _apply_ref_rewrite(ref, {}) == ref


# ---------------------------------------------------------------------------
# _rewrite_refs
# ---------------------------------------------------------------------------


class TestRewriteRefs:
    def test_rewrites_ref_in_dict(self) -> None:
        rewrites = {CORE_REC: f"{BASE}adm/core/BENCHLING/2023/09/core.schema"}
        schema: dict[str, Any] = {"$ref": f"{CORE_REC}#/$defs/SomeType"}
        result = _rewrite_refs(schema, rewrites)
        assert result["$ref"].startswith(
            f"{BASE}adm/core/BENCHLING/2023/09/core.schema"
        )

    def test_rewrites_id(self) -> None:
        rewrites = {CORE_REC: f"{BASE}adm/core/BENCHLING/2023/09/core.schema"}
        schema: dict[str, Any] = {"$id": CORE_REC}
        result = _rewrite_refs(schema, rewrites)
        assert "BENCHLING" in result["$id"]

    def test_recurses_into_nested_dicts(self) -> None:
        rewrites = {CORE_REC: f"{BASE}adm/core/BENCHLING/2023/09/core.schema"}
        schema: dict[str, Any] = {
            "properties": {"field": {"$ref": f"{CORE_REC}#/$defs/SomeType"}}
        }
        result = _rewrite_refs(schema, rewrites)
        assert "BENCHLING" in result["properties"]["field"]["$ref"]

    def test_recurses_into_lists(self) -> None:
        rewrites = {CORE_REC: f"{BASE}adm/core/BENCHLING/2023/09/core.schema"}
        schema: list[Any] = [{"$ref": f"{CORE_REC}#/$defs/SomeType"}]
        result = _rewrite_refs(schema, rewrites)
        assert "BENCHLING" in result[0]["$ref"]

    def test_leaves_non_matching_refs(self) -> None:
        schema: dict[str, Any] = {"$ref": "#/$defs/localType"}
        result = _rewrite_refs(schema, {})
        assert result["$ref"] == "#/$defs/localType"

    def test_scalar_passthrough(self) -> None:
        assert _rewrite_refs("hello", {}) == "hello"
        assert _rewrite_refs(42, {}) == 42


# ---------------------------------------------------------------------------
# _deep_merge
# ---------------------------------------------------------------------------


class TestDeepMerge:
    def test_overlay_wins_for_scalars(self) -> None:
        result = _deep_merge({"a": 1}, {"a": 2})
        assert result["a"] == 2

    def test_new_keys_added(self) -> None:
        result = _deep_merge({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_recursive_dict_merge(self) -> None:
        base: dict[str, Any] = {"nested": {"x": 1, "y": 2}}
        overlay: dict[str, Any] = {"nested": {"y": 3, "z": 4}}
        result = _deep_merge(base, overlay)
        assert result["nested"] == {"x": 1, "y": 3, "z": 4}

    def test_base_not_mutated(self) -> None:
        base: dict[str, Any] = {"a": {"b": 1}}
        overlay: dict[str, Any] = {"a": {"c": 2}}
        _deep_merge(base, overlay)
        assert "c" not in base["a"]

    def test_non_dict_overlay_replaces_dict(self) -> None:
        result = _deep_merge({"a": {"nested": True}}, {"a": "string"})
        assert result["a"] == "string"


# ---------------------------------------------------------------------------
# _strip_embedded_defs
# ---------------------------------------------------------------------------


class TestStripEmbeddedDefs:
    def test_removes_url_keyed_defs(self) -> None:
        schema: dict[str, Any] = {
            "$defs": {
                "normalType": {"type": "string"},
                "http://example.com/embedded": {"type": "object"},
            }
        }
        _strip_embedded_defs(schema)
        assert "http://example.com/embedded" not in schema["$defs"]
        assert "normalType" in schema["$defs"]

    def test_removes_empty_defs(self) -> None:
        schema: dict[str, Any] = {"$defs": {"http://example.com/schema": {}}}
        _strip_embedded_defs(schema)
        assert "$defs" not in schema

    def test_noop_without_url_keys(self) -> None:
        schema: dict[str, Any] = {"$defs": {"myType": {"type": "string"}}}
        _strip_embedded_defs(schema)
        assert "myType" in schema["$defs"]

    def test_noop_without_defs(self) -> None:
        schema: dict[str, Any] = {"type": "object"}
        _strip_embedded_defs(schema)  # should not raise
        assert "$defs" not in schema


# ---------------------------------------------------------------------------
# _fork_benchling_shared_schemas
# ---------------------------------------------------------------------------


class TestForkBenchlingSharedSchemas:
    def test_forks_rec_into_benchling(self) -> None:
        core_schema: dict[str, Any] = {
            "$defs": {"someType": {"type": "string"}},
        }
        benchling_technique: dict[str, Any] = {
            "$defs": {
                CORE_REC: {
                    "$defs": {"extraType": {"type": "number"}},
                },
            },
            "allOf": [{"$ref": f"{CORE_REC}#/$defs/someType"}],
        }
        all_schemas: dict[str, Any] = {
            CORE_REC: core_schema,
            TECHNIQUE_BENCHLING: benchling_technique,
        }
        _fork_benchling_shared_schemas(all_schemas)

        # A BENCHLING-versioned core schema should now exist
        benchling_core = f"{BASE}adm/core/BENCHLING/2023/09/core.schema"
        assert benchling_core in all_schemas
        # The forked schema should have the original + additions merged
        assert "someType" in all_schemas[benchling_core].get("$defs", {})

    def test_rec_schemas_untouched(self) -> None:
        core_schema: dict[str, Any] = {
            "$defs": {"someType": {"type": "string"}},
        }
        benchling_technique: dict[str, Any] = {
            "$defs": {
                CORE_REC: {
                    "$defs": {"extraType": {"type": "number"}},
                },
            },
        }
        all_schemas: dict[str, Any] = {
            CORE_REC: core_schema,
            TECHNIQUE_BENCHLING: benchling_technique,
        }
        _fork_benchling_shared_schemas(all_schemas)

        # Original REC schema must not be modified
        assert all_schemas[CORE_REC] == {
            "$defs": {"someType": {"type": "string"}},
        }

    def test_refs_rewritten_to_benchling(self) -> None:
        core_schema: dict[str, Any] = {
            "$defs": {"someType": {"type": "string"}},
        }
        benchling_technique: dict[str, Any] = {
            "$defs": {
                CORE_REC: {
                    "$defs": {"extraType": {"type": "number"}},
                },
            },
            "allOf": [{"$ref": f"{CORE_REC}#/$defs/someType"}],
        }
        all_schemas: dict[str, Any] = {
            CORE_REC: core_schema,
            TECHNIQUE_BENCHLING: benchling_technique,
        }
        _fork_benchling_shared_schemas(all_schemas)

        # The technique schema's $ref should now point to BENCHLING version
        ref = all_schemas[TECHNIQUE_BENCHLING]["allOf"][0]["$ref"]
        assert "/BENCHLING/" in ref

    def test_url_keyed_defs_stripped(self) -> None:
        core_schema: dict[str, Any] = {
            "$defs": {"someType": {"type": "string"}},
        }
        benchling_technique: dict[str, Any] = {
            "$defs": {
                CORE_REC: {
                    "$defs": {"extraType": {"type": "number"}},
                },
            },
        }
        all_schemas: dict[str, Any] = {
            CORE_REC: core_schema,
            TECHNIQUE_BENCHLING: benchling_technique,
        }
        _fork_benchling_shared_schemas(all_schemas)

        # URL-keyed $defs should be stripped from the technique schema
        for key in all_schemas[TECHNIQUE_BENCHLING].get("$defs", {}):
            assert not key.startswith("http://")

    def test_non_benchling_schemas_ignored(self) -> None:
        rec_technique = f"{BASE}adm/test/REC/2024/09/test.schema"
        all_schemas: dict[str, Any] = {
            rec_technique: {
                "$defs": {"http://example.com/something": {"extra": True}},
            },
        }
        _fork_benchling_shared_schemas(all_schemas)
        # REC schemas with URL-keyed defs are not forked (only BENCHLING schemas are)
        assert len(all_schemas) == 1


# ---------------------------------------------------------------------------
# _extract_descriptive_name
# ---------------------------------------------------------------------------


class TestExtractDescriptiveName:
    def test_iri_correction_takes_priority(self) -> None:
        result = _extract_descriptive_name(
            "RU.s",
            {"properties": {"unit": {"$asm.unit-iri": "http://qudt.org#Foo"}}},
            "Bar",
        )
        assert result == "ResponseUnitTimesSecond"

    def test_iri_fragment(self) -> None:
        schema: dict[str, Any] = {
            "properties": {
                "unit": {"$asm.unit-iri": "http://qudt.org/vocab/unit#DegreeCelsius"}
            }
        }
        result = _extract_descriptive_name("degC", schema, "some_key")
        assert result == "DegreeCelsius"

    def test_descriptive_def_key(self) -> None:
        result = _extract_descriptive_name("degC", {}, "DegreeCelsius")
        assert result == "DegreeCelsius"

    def test_fallback_to_symbol(self) -> None:
        result = _extract_descriptive_name("mL", {}, "m_l_lowercase")
        # Falls through to unit_symbol_to_class_name since key doesn't start with uppercase
        assert isinstance(result, str)
        assert len(result) > 0

    def test_def_key_with_special_chars_not_used(self) -> None:
        result = _extract_descriptive_name("mAU", {}, "http://example.com/mAU")
        # Key starting with lowercase or containing / should not be used as descriptive name
        assert result != "http://example.com/mAU"
