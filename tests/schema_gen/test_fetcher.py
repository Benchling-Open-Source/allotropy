"""Tests for allotropy.schema_gen.fetcher — dependency ordering and ref walking."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from allotropy.schema_gen.fetcher import build_dependency_order, SchemaFetcher

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

    def test_circular_dependency_deterministic(self) -> None:
        """Circular deps should be appended in sorted order for reproducibility."""
        url_a = f"{BASE}adm/a/REC/2024/09/a.schema"
        url_b = f"{BASE}adm/b/REC/2024/09/b.schema"
        url_c = f"{BASE}adm/c/REC/2024/09/c.schema"
        schemas = {
            url_a: {"$defs": {"x": {"$ref": f"{url_b}#/$defs/y"}}},
            url_b: {"$defs": {"y": {"$ref": f"{url_c}#/$defs/z"}}},
            url_c: {"$defs": {"z": {"$ref": f"{url_a}#/$defs/x"}}},
        }
        # Run multiple times — result must be identical each time
        results = [build_dependency_order(schemas) for _ in range(10)]
        assert all(r == results[0] for r in results)

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


class TestSchemaFetcher:
    def test_cache_hit(self, tmp_path: Path) -> None:
        """When a schema is cached on disk, no network request is made."""
        url = f"{BASE}adm/core/REC/2024/09/core.schema"
        schema = {"$defs": {"x": {"type": "string"}}}

        # Pre-populate cache
        from allotropy.schema_gen.naming import schema_url_to_cache_path

        cache_path = schema_url_to_cache_path(url, tmp_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(schema, f)

        fetcher = SchemaFetcher(cache_dir=tmp_path)
        result = fetcher.fetch_with_dependencies(url)
        assert url in result
        assert result[url] == schema

    def test_cache_miss_no_network_raises(self, tmp_path: Path) -> None:
        """Missing cache + unreachable URL raises RuntimeError."""
        url = f"{BASE}adm/fake/REC/2099/01/nonexistent.schema"
        fetcher = SchemaFetcher(cache_dir=tmp_path)
        with pytest.raises(RuntimeError, match="Schema not found|Network error"):
            fetcher.fetch_with_dependencies(url)

    def test_recursive_dependencies_from_cache(self, tmp_path: Path) -> None:
        """Fetcher resolves $ref chains from cached files without network."""
        url_a = f"{BASE}adm/a/REC/2024/09/a.schema"
        url_b = f"{BASE}adm/b/REC/2024/09/b.schema"
        schema_a = {"$defs": {"x": {"type": "string"}}}
        schema_b = {"$defs": {"y": {"$ref": f"{url_a}#/$defs/x"}}}

        from allotropy.schema_gen.naming import schema_url_to_cache_path

        for url, schema in [(url_a, schema_a), (url_b, schema_b)]:
            cache_path = schema_url_to_cache_path(url, tmp_path)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump(schema, f)

        fetcher = SchemaFetcher(cache_dir=tmp_path)
        result = fetcher.fetch_with_dependencies(url_b)
        assert url_a in result
        assert url_b in result
