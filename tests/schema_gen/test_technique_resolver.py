"""Tests for allotropy.schema_gen.technique_resolver."""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import patch

import click
import pytest

from allotropy.schema_gen.technique_resolver import (
    _list_cached_schemas,
    _list_cached_techniques,
    is_shorthand,
    list_gitlab_techniques,
    list_schemas_in_directory,
    parse_shorthand,
    resolve_shorthand_to_urls,
    resolve_technique_name,
)

ALLOTROPE_PREFIX = "http://purl.allotrope.org/json-schemas/"


class TestIsShorthand:
    def test_full_http_url(self) -> None:
        assert not is_shorthand(
            "http://purl.allotrope.org/json-schemas/adm/pcr/REC/2024/09/qpcr.schema"
        )

    def test_full_https_url(self) -> None:
        assert not is_shorthand(
            "https://gitlab.com/allotrope-public/asm/-/raw/main/json-schemas/adm/pcr/REC/2024/09/qpcr.schema.json"
        )

    def test_shorthand_simple(self) -> None:
        assert is_shorthand("plate-reader 2026/03")

    def test_shorthand_with_status(self) -> None:
        assert is_shorthand("pcr WD/2025/06")

    def test_shorthand_with_underscores(self) -> None:
        assert is_shorthand("plate_reader 2026/03")


class TestParseShorthand:
    def test_simple(self) -> None:
        assert parse_shorthand("plate-reader 2026/03") == (
            "plate-reader",
            "REC",
            "2026",
            "03",
        )

    def test_with_status_rec(self) -> None:
        assert parse_shorthand("pcr REC/2024/09") == ("pcr", "REC", "2024", "09")

    def test_with_status_wd(self) -> None:
        assert parse_shorthand("pcr WD/2025/06") == ("pcr", "WD", "2025", "06")

    def test_with_status_benchling(self) -> None:
        assert parse_shorthand("chromatography BENCHLING/2024/11") == (
            "chromatography",
            "BENCHLING",
            "2024",
            "11",
        )

    def test_case_insensitive_status(self) -> None:
        assert parse_shorthand("pcr rec/2024/09") == ("pcr", "REC", "2024", "09")

    def test_case_insensitive_technique(self) -> None:
        technique, _, _, _ = parse_shorthand("Plate-Reader 2026/03")
        assert technique == "plate-reader"

    def test_underscores_in_technique(self) -> None:
        technique, _, _, _ = parse_shorthand("plate_reader 2026/03")
        assert technique == "plate_reader"

    def test_strips_whitespace(self) -> None:
        assert parse_shorthand("  plate-reader 2026/03  ") == (
            "plate-reader",
            "REC",
            "2026",
            "03",
        )

    def test_invalid_format_no_version(self) -> None:
        with pytest.raises(click.UsageError, match="Invalid shorthand format"):
            parse_shorthand("plate-reader")

    def test_invalid_format_garbage(self) -> None:
        with pytest.raises(click.UsageError, match="Invalid shorthand format"):
            parse_shorthand("just some random text")

    def test_invalid_status(self) -> None:
        with pytest.raises(click.UsageError, match="Invalid status"):
            parse_shorthand("pcr FAKE/2024/09")


def _mock_urlopen(entries: list[dict[str, Any]]) -> BytesIO:
    """Create a mock urlopen response with the given JSON entries."""
    data = json.dumps(entries).encode("utf-8")
    return BytesIO(data)


def _tree_entry(name: str, entry_type: str = "tree") -> dict[str, str]:
    """Create a minimal GitLab API tree entry."""
    return {"name": name, "type": entry_type, "path": f"json-schemas/adm/{name}"}


def _blob_entry(name: str, path: str = "") -> dict[str, str]:
    return {"name": name, "type": "blob", "path": path or name}


class TestListGitlabTechniques:
    def test_returns_sorted_tree_entries(self) -> None:
        entries = [
            _tree_entry("pcr"),
            _tree_entry("absorbance"),
            _tree_entry("plate-reader"),
        ]
        with patch(
            "allotropy.schema_gen.technique_resolver.urlopen",
            return_value=_mock_urlopen(entries),
        ):
            result = list_gitlab_techniques()
        assert result == ["absorbance", "pcr", "plate-reader"]

    def test_filters_non_tree_entries(self) -> None:
        entries = [
            _tree_entry("pcr"),
            _blob_entry("README.md"),
            _tree_entry("absorbance"),
        ]
        with patch(
            "allotropy.schema_gen.technique_resolver.urlopen",
            return_value=_mock_urlopen(entries),
        ):
            result = list_gitlab_techniques()
        assert result == ["absorbance", "pcr"]


class TestResolveTechniqueName:
    TECHNIQUES: ClassVar[list[str]] = [
        "absorbance",
        "cell-counting",
        "cell-culture-analyzer",
        "pcr",
        "plate-reader",
        "solution-analyzer",
    ]

    def test_exact_match(self) -> None:
        assert resolve_technique_name("plate-reader", self.TECHNIQUES) == "plate-reader"

    def test_normalized_match_underscores(self) -> None:
        assert resolve_technique_name("plate_reader", self.TECHNIQUES) == "plate-reader"

    def test_normalized_match_uppercase(self) -> None:
        assert resolve_technique_name("PCR", self.TECHNIQUES) == "pcr"

    def test_fuzzy_single_match_accepted(self) -> None:
        with patch("click.confirm", return_value=True):
            result = resolve_technique_name("platereader", self.TECHNIQUES)
        assert result == "plate-reader"

    def test_fuzzy_single_match_declined(self) -> None:
        with patch("click.confirm", return_value=False):
            with pytest.raises(click.Abort):
                resolve_technique_name("platereader", self.TECHNIQUES)

    def test_no_matches_aborts(self) -> None:
        with pytest.raises(click.Abort):
            resolve_technique_name("xyzzy", self.TECHNIQUES)


class TestListSchemasInDirectory:
    def test_returns_schema_files(self) -> None:
        entries = [
            _blob_entry("plate-reader.schema.json"),
            _blob_entry("plate-reader.embed.schema.json"),
        ]
        with patch(
            "allotropy.schema_gen.technique_resolver.urlopen",
            return_value=_mock_urlopen(entries),
        ):
            result = list_schemas_in_directory("plate-reader", "REC", "2026", "03")
        assert result == ["plate-reader.schema.json"]

    def test_multiple_schemas(self) -> None:
        entries = [
            _blob_entry("dpcr.schema.json"),
            _blob_entry("dpcr.embed.schema.json"),
            _blob_entry("qpcr.schema.json"),
            _blob_entry("qpcr.embed.schema.json"),
        ]
        with patch(
            "allotropy.schema_gen.technique_resolver.urlopen",
            return_value=_mock_urlopen(entries),
        ):
            result = list_schemas_in_directory("pcr", "REC", "2026", "03")
        assert result == ["dpcr.schema.json", "qpcr.schema.json"]

    def test_filters_directories(self) -> None:
        entries = [
            _tree_entry("subdir"),
            _blob_entry("test.schema.json"),
        ]
        with patch(
            "allotropy.schema_gen.technique_resolver.urlopen",
            return_value=_mock_urlopen(entries),
        ):
            result = list_schemas_in_directory("test", "REC", "2026", "03")
        assert result == ["test.schema.json"]


class TestResolveShorthandToUrls:
    def _mock_techniques(self) -> list[dict[str, str]]:
        return [
            _tree_entry("pcr"),
            _tree_entry("plate-reader"),
        ]

    def _mock_schemas(self) -> list[dict[str, str]]:
        return [
            _blob_entry("plate-reader.schema.json"),
            _blob_entry("plate-reader.embed.schema.json"),
        ]

    def test_resolves_to_purl_urls(self) -> None:
        techniques = self._mock_techniques()
        schemas = self._mock_schemas()

        def mock_urlopen(url: str, **_kwargs: Any) -> BytesIO:
            if "path=json-schemas/adm&" in url:
                return _mock_urlopen(techniques)
            return _mock_urlopen(schemas)

        with patch(
            "allotropy.schema_gen.technique_resolver.urlopen",
            side_effect=mock_urlopen,
        ):
            result = resolve_shorthand_to_urls("plate-reader 2026/03")

        assert result == [
            f"{ALLOTROPE_PREFIX}adm/plate-reader/REC/2026/03/plate-reader.schema"
        ]

    def test_multi_schema_technique(self) -> None:
        techniques = self._mock_techniques()
        pcr_schemas = [
            _blob_entry("dpcr.schema.json"),
            _blob_entry("dpcr.embed.schema.json"),
            _blob_entry("qpcr.schema.json"),
            _blob_entry("qpcr.embed.schema.json"),
        ]

        def mock_urlopen(url: str, **_kwargs: Any) -> BytesIO:
            if "path=json-schemas/adm&" in url:
                return _mock_urlopen(techniques)
            return _mock_urlopen(pcr_schemas)

        with patch(
            "allotropy.schema_gen.technique_resolver.urlopen",
            side_effect=mock_urlopen,
        ):
            result = resolve_shorthand_to_urls("pcr 2026/03")

        assert result == [
            f"{ALLOTROPE_PREFIX}adm/pcr/REC/2026/03/dpcr.schema",
            f"{ALLOTROPE_PREFIX}adm/pcr/REC/2026/03/qpcr.schema",
        ]


class TestCacheFallback:
    def test_list_cached_techniques(self, tmp_path: Path) -> None:
        adm = tmp_path / "adm"
        (adm / "pcr").mkdir(parents=True)
        (adm / "plate-reader").mkdir()
        (adm / "core").mkdir()  # should be excluded
        (adm / "qudt").mkdir()  # should be excluded
        result = _list_cached_techniques(tmp_path)
        assert result == ["pcr", "plate-reader"]

    def test_list_cached_techniques_empty(self, tmp_path: Path) -> None:
        assert _list_cached_techniques(tmp_path) == []

    def test_list_cached_schemas(self, tmp_path: Path) -> None:
        schema_dir = tmp_path / "adm" / "pcr" / "REC" / "2026" / "03"
        schema_dir.mkdir(parents=True)
        (schema_dir / "qpcr.schema.json").write_text("{}")
        (schema_dir / "qpcr.embed.schema.json").write_text("{}")
        (schema_dir / "dpcr.schema.json").write_text("{}")
        result = _list_cached_schemas("pcr", "REC", "2026", "03", tmp_path)
        assert result == ["dpcr.schema.json", "qpcr.schema.json"]

    def test_list_cached_schemas_missing_dir(self, tmp_path: Path) -> None:
        assert _list_cached_schemas("pcr", "REC", "2026", "03", tmp_path) == []

    def test_list_gitlab_techniques_falls_back_to_cache(self) -> None:
        """When GitLab API fails, falls back to local cache."""
        with (
            patch(
                "allotropy.schema_gen.technique_resolver._gitlab_tree",
                return_value=None,
            ),
            patch(
                "allotropy.schema_gen.technique_resolver._list_cached_techniques",
                return_value=["pcr", "plate-reader"],
            ),
        ):
            result = list_gitlab_techniques()
        assert result == ["pcr", "plate-reader"]

    def test_list_gitlab_techniques_no_cache_raises(self) -> None:
        """When GitLab API fails and no cache, raises ClickException."""
        with (
            patch(
                "allotropy.schema_gen.technique_resolver._gitlab_tree",
                return_value=None,
            ),
            patch(
                "allotropy.schema_gen.technique_resolver._list_cached_techniques",
                return_value=[],
            ),
            pytest.raises(click.ClickException),
        ):
            list_gitlab_techniques()

    def test_list_schemas_falls_back_to_cache(self) -> None:
        """When GitLab API fails for schema listing, falls back to local cache."""
        with (
            patch(
                "allotropy.schema_gen.technique_resolver._gitlab_tree",
                return_value=None,
            ),
            patch(
                "allotropy.schema_gen.technique_resolver._list_cached_schemas",
                return_value=["plate-reader.schema.json"],
            ),
        ):
            result = list_schemas_in_directory("plate-reader", "REC", "2026", "03")
        assert result == ["plate-reader.schema.json"]

    def test_list_schemas_no_cache_raises(self) -> None:
        """When GitLab API fails and no cache, raises ClickException."""
        with (
            patch(
                "allotropy.schema_gen.technique_resolver._gitlab_tree",
                return_value=None,
            ),
            patch(
                "allotropy.schema_gen.technique_resolver._list_cached_schemas",
                return_value=[],
            ),
            pytest.raises(click.ClickException),
        ):
            list_schemas_in_directory("plate-reader", "REC", "2026", "03")
