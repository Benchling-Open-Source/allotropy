"""Tests for allotropy.schema_gen.fetcher — dependency ordering and ref walking."""

from __future__ import annotations

from typing import Any

from allotropy.schema_gen.fetcher import build_dependency_order

BASE = "http://purl.allotrope.org/json-schemas/"


class TestBuildDependencyOrder:
    def test_single_schema_no_deps(self) -> None:
        url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas = {url: {"$defs": {"foo": {"type": "string"}}}}
        result = build_dependency_order(schemas)
        assert result == [url]

    def test_linear_dependency_chain(self) -> None:
        url_a = f"{BASE}adm/a/REC/2024/09/a.schema"
        url_b = f"{BASE}adm/b/REC/2024/09/b.schema"
        url_c = f"{BASE}adm/c/REC/2024/09/c.schema"
        schemas = {
            url_a: {"$defs": {"x": {"type": "string"}}},
            url_b: {"$defs": {"y": {"$ref": f"{url_a}#/$defs/x"}}},
            url_c: {"$defs": {"z": {"$ref": f"{url_b}#/$defs/y"}}},
        }
        result = build_dependency_order(schemas)
        assert result.index(url_a) < result.index(url_b)
        assert result.index(url_b) < result.index(url_c)

    def test_independent_schemas(self) -> None:
        url_a = f"{BASE}adm/a/REC/2024/09/a.schema"
        url_b = f"{BASE}adm/b/REC/2024/09/b.schema"
        schemas = {
            url_a: {"$defs": {"x": {"type": "string"}}},
            url_b: {"$defs": {"y": {"type": "integer"}}},
        }
        result = build_dependency_order(schemas)
        assert set(result) == {url_a, url_b}

    def test_diamond_dependency(self) -> None:
        url_base = f"{BASE}adm/base/REC/2024/09/base.schema"
        url_left = f"{BASE}adm/left/REC/2024/09/left.schema"
        url_right = f"{BASE}adm/right/REC/2024/09/right.schema"
        url_top = f"{BASE}adm/top/REC/2024/09/top.schema"
        schemas: dict[str, dict[str, Any]] = {
            url_base: {"$defs": {"x": {"type": "string"}}},
            url_left: {"$defs": {"l": {"$ref": f"{url_base}#/$defs/x"}}},
            url_right: {"$defs": {"r": {"$ref": f"{url_base}#/$defs/x"}}},
            url_top: {
                "$defs": {
                    "t": {
                        "properties": {
                            "a": {"$ref": f"{url_left}#/$defs/l"},
                            "b": {"$ref": f"{url_right}#/$defs/r"},
                        }
                    }
                }
            },
        }
        result = build_dependency_order(schemas)
        assert result.index(url_base) < result.index(url_left)
        assert result.index(url_base) < result.index(url_right)
        assert result.index(url_left) < result.index(url_top)
        assert result.index(url_right) < result.index(url_top)

    def test_external_refs_ignored(self) -> None:
        """Refs to schemas not in the input set are ignored."""
        url = f"{BASE}adm/test/REC/2024/09/test.schema"
        external = f"{BASE}adm/external/REC/2024/09/external.schema"
        schemas = {
            url: {"$defs": {"x": {"$ref": f"{external}#/$defs/y"}}},
        }
        result = build_dependency_order(schemas)
        assert result == [url]

    def test_circular_dependency_handled(self) -> None:
        """Circular deps shouldn't crash — remaining schemas appended."""
        url_a = f"{BASE}adm/a/REC/2024/09/a.schema"
        url_b = f"{BASE}adm/b/REC/2024/09/b.schema"
        schemas = {
            url_a: {"$defs": {"x": {"$ref": f"{url_b}#/$defs/y"}}},
            url_b: {"$defs": {"y": {"$ref": f"{url_a}#/$defs/x"}}},
        }
        result = build_dependency_order(schemas)
        assert set(result) == {url_a, url_b}

    def test_nested_refs_in_properties(self) -> None:
        url_core = f"{BASE}adm/core/REC/2024/09/core.schema"
        url_tech = f"{BASE}adm/tech/REC/2024/09/tech.schema"
        schemas: dict[str, dict[str, Any]] = {
            url_core: {"$defs": {"base": {"type": "string"}}},
            url_tech: {
                "$defs": {
                    "doc": {
                        "type": "object",
                        "properties": {
                            "field_a": {
                                "allOf": [
                                    {"$ref": f"{url_core}#/$defs/base"},
                                    {"enum": ["x"]},
                                ]
                            }
                        },
                    }
                }
            },
        }
        result = build_dependency_order(schemas)
        assert result.index(url_core) < result.index(url_tech)
