"""Test that generated models are up-to-date with cached schemas.

Running schema generation on all cached schemas must produce identical output
to what is already committed. If this test fails, run:

    hatch run scripts:generate-schemas <url>

for the affected schema(s) and commit the result.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from allotropy.allotrope.path_util import SCHEMA_DIR_PATH
from allotropy.schema_gen.generate import generate_models
from allotropy.schema_gen.naming import ALLOTROPE_URL_PREFIX, DEFAULT_MODEL_OUTPUT_DIR


def _collect_all_schema_urls() -> list[str]:
    """Collect canonical URLs for all cached schemas.

    Includes core, qudt, and technique schemas so that shared modules
    are also regenerated and verified.
    """
    urls: list[str] = []
    for f in sorted(SCHEMA_DIR_PATH.rglob("*.schema.json")):
        # Skip .embed. / .tabular. cache copies
        if ".embed." in f.name or ".tabular." in f.name:
            continue
        rel = f.relative_to(SCHEMA_DIR_PATH)
        url_path = str(rel).removesuffix(".json")
        urls.append(ALLOTROPE_URL_PREFIX + url_path)
    return urls


def _extract_class_blocks(source: str) -> str:
    """Extract everything from the first class/decorator definition onward.

    When generating into a temp directory, ruff's lint behaviour differs from
    in-project linting (the project's pyproject.toml suppresses PLC0414 for
    model files, but ruff can't find that config in /tmp).  This causes
    re-export import lines (``X as X``) to be stripped in temp output.

    Comparing from the first ``class`` or ``@dataclass`` line skips the
    import header entirely, catching all meaningful differences (class
    definitions, fields, type aliases) without being affected by lint
    environment differences.
    """
    match = re.search(r"^(class |@dataclass)", source, re.MULTILINE)
    return source[match.start() :] if match else source


def _assert_generated_matches_committed(
    tmp_path: Path,
    schema_urls: str | list[str],
) -> None:
    """Generate schemas into *tmp_path* and compare against committed models.

    Compares class definitions (everything after the import header) rather
    than full file contents.  This is necessary because ruff's lint behaviour
    differs for files outside the project tree: the project's pyproject.toml
    suppresses PLC0414 (import-self-alias) for model files, but ruff can't
    find that config when the file lives in a temp directory, causing
    re-export imports (``X as X``) to be stripped.
    """
    generate_models(schema_urls, output_dir=tmp_path)

    for generated_file in sorted(tmp_path.rglob("*.py")):
        rel = generated_file.relative_to(tmp_path)
        committed = DEFAULT_MODEL_OUTPUT_DIR / rel
        assert committed.exists(), f"Unexpected file generated: {rel}"
        generated_src = generated_file.read_text(encoding="utf-8")
        committed_src = committed.read_text(encoding="utf-8")
        assert _extract_class_blocks(generated_src) == _extract_class_blocks(
            committed_src
        ), (
            f"Generated output differs from committed for {rel}.\n"
            "Run 'hatch run scripts:generate-schemas' for the affected schema(s) "
            "and commit the result."
        )


@pytest.mark.long
def test_generated_models_are_up_to_date(tmp_path: Path) -> None:
    """Regenerating all schemas must produce class definitions identical to committed models."""
    urls = _collect_all_schema_urls()
    assert urls, "No schemas found — check SCHEMA_DIR_PATH"
    _assert_generated_matches_committed(tmp_path, urls)


@pytest.mark.long
def test_single_schema_generation_is_idempotent(tmp_path: Path) -> None:
    """Generating a single schema must match committed models.

    This catches regressions where shared modules (core.py, hierarchy.py, etc.)
    produce different output depending on which schemas are included in a run —
    e.g., BENCHLING additions leaking into REC shared modules.
    """
    urls = _collect_all_schema_urls()
    # Pick a REC technique schema (not core/qudt — we want one that pulls in
    # shared dependencies, which is where single-vs-batch divergence appears).
    rec_technique_urls = [
        u
        for u in urls
        if "/adm/" in u
        and "/core/" not in u
        and "/BENCHLING/" not in u
        and "units.schema" not in u
    ]
    assert rec_technique_urls, "No REC technique schemas found"
    _assert_generated_matches_committed(tmp_path, rec_technique_urls[0])
