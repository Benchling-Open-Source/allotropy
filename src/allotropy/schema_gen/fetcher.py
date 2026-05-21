"""Schema fetcher: download and cache Allotrope JSON schemas from GitLab.

Given a starting schema URL, discovers all $ref dependencies recursively
and downloads them all to a local cache directory.
"""

from __future__ import annotations

from collections import deque
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from allotropy.schema_gen.naming import (
    DEFAULT_SCHEMA_CACHE_DIR,
    gitlab_blob_to_raw,
    normalize_schema_url,
    schema_url_to_cache_path,
)


class SchemaFetcher:
    """Downloads and caches Allotrope JSON schemas."""

    def __init__(self, cache_dir: Path = DEFAULT_SCHEMA_CACHE_DIR) -> None:
        self.cache_dir = cache_dir
        self._schemas: dict[str, dict[str, Any]] = {}

    @property
    def schemas(self) -> dict[str, dict[str, Any]]:
        """All fetched schemas, keyed by canonical URL."""
        return self._schemas

    def fetch_with_dependencies(self, url: str) -> dict[str, dict[str, Any]]:
        """Fetch a schema and all its $ref dependencies recursively.

        Args:
            url: Any supported URL format (GitLab blob/raw, Allotrope).

        Returns:
            Dict mapping canonical schema URLs to parsed JSON schema dicts.
        """
        canonical = self._to_canonical(url)
        self._fetch_recursive(canonical)
        return self._schemas

    def _fetch_recursive(self, canonical_url: str) -> None:
        """Recursively fetch a schema and its dependencies."""
        if canonical_url in self._schemas:
            return

        schema = self._download_schema(canonical_url)
        self._schemas[canonical_url] = schema

        # Find all external $ref URLs in this schema
        ref_urls = self._extract_external_refs(schema)
        for ref_url in ref_urls:
            self._fetch_recursive(ref_url)

    def _download_schema(self, canonical_url: str) -> dict[str, Any]:
        """Download a schema, using cache if available."""
        cache_path = schema_url_to_cache_path(canonical_url, self.cache_dir)

        # Check cache first
        if cache_path.exists():
            with open(cache_path, encoding="utf-8") as f:
                result: dict[str, Any] = json.load(f)
                return result

        # Download via purl redirect (canonical URL + .json suffix)
        purl_url = (
            canonical_url + ".json"
            if not canonical_url.endswith(".json")
            else canonical_url
        )
        print(f"  Downloading: {purl_url}")
        try:
            with urlopen(purl_url, timeout=30) as response:  # noqa: S310
                data = response.read().decode("utf-8")
        except HTTPError as exc:
            msg = f"Schema not found (HTTP {exc.code}): {canonical_url}\n  URL: {purl_url}"
            raise RuntimeError(msg) from exc
        except URLError as exc:
            msg = f"Network error downloading schema: {canonical_url}\n  URL: {purl_url}\n  {exc.reason}"
            raise RuntimeError(msg) from exc

        schema: dict[str, Any] = json.loads(data)

        # Cache locally
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

        return schema

    def _extract_external_refs(self, schema: dict[str, Any]) -> set[str]:
        """Extract all external schema URLs referenced by $ref in a schema."""
        refs: set[str] = set()
        _walk_refs_for_deps(schema, refs)
        return refs

    def _to_canonical(self, url: str) -> str:
        """Convert any URL format to canonical Allotrope URL."""
        # Handle GitLab blob URLs
        if "/-/blob/" in url:
            url = gitlab_blob_to_raw(url)

        # Handle query parameters
        url = url.split("?")[0]

        return normalize_schema_url(url)


def build_dependency_order(schemas: dict[str, dict[str, Any]]) -> list[str]:
    """Return schema URLs in dependency order (dependencies first).

    Uses topological sort based on $ref relationships.
    """
    # Build adjacency list: schema -> set of schemas it depends on
    deps: dict[str, set[str]] = {url: set() for url in schemas}

    for url, schema in schemas.items():
        refs: set[str] = set()
        _walk_refs_for_deps(schema, refs)
        # Only keep refs that are in our schema set
        deps[url] = refs & set(schemas.keys())

    # Topological sort (Kahn's algorithm)
    in_degree = {url: len(dep_set) for url, dep_set in deps.items()}

    queue: deque[str] = deque(url for url, deg in in_degree.items() if deg == 0)
    result: list[str] = []

    while queue:
        url = queue.popleft()
        result.append(url)
        # For each schema that depends on `url`, decrement its in-degree
        for other_url, dep_set in deps.items():
            if url in dep_set:
                in_degree[other_url] -= 1
                if in_degree[other_url] == 0:
                    queue.append(other_url)

    if len(result) != len(schemas):
        # Circular dependency — add remaining in sorted order for reproducibility
        remaining = sorted(set(schemas.keys()) - set(result))
        result.extend(remaining)

    return result


def _walk_refs_for_deps(obj: Any, refs: set[str]) -> None:
    """Walk schema and collect canonical URLs of external $ref targets."""
    if isinstance(obj, dict):
        if "$ref" in obj:
            ref = obj["$ref"]
            if not ref.startswith("#"):
                schema_url = ref.split("#")[0]
                try:
                    refs.add(normalize_schema_url(schema_url))
                except ValueError:
                    pass
        for value in obj.values():
            _walk_refs_for_deps(value, refs)
    elif isinstance(obj, list):
        for item in obj:
            _walk_refs_for_deps(item, refs)
