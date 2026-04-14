"""Test that generated models are up-to-date with cached schemas.

Running schema generation on all cached schemas must produce identical output
to what is already committed. If this test fails, run:

    hatch run scripts:generate-schemas <url>

for the affected schema(s) and commit the result.
"""

from __future__ import annotations

import hashlib
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


def _snapshot_model_files() -> dict[str, str]:
    """Return {relative_path: md5} for all generated model .py files."""
    snapshot: dict[str, str] = {}
    for f in sorted(DEFAULT_MODEL_OUTPUT_DIR.rglob("*.py")):
        rel = str(f.relative_to(DEFAULT_MODEL_OUTPUT_DIR))
        snapshot[rel] = hashlib.md5(f.read_bytes()).hexdigest()  # noqa: S324
    return snapshot


@pytest.mark.long
def test_generated_models_are_up_to_date() -> None:
    """Regenerating all schemas must produce no changes to committed models."""
    before = _snapshot_model_files()

    urls = _collect_all_schema_urls()
    assert urls, "No schemas found — check SCHEMA_DIR_PATH"

    generate_models(urls)

    after = _snapshot_model_files()

    added = set(after) - set(before)
    removed = set(before) - set(after)
    changed = {k for k in set(before) & set(after) if before[k] != after[k]}

    messages: list[str] = []
    if added:
        messages.append(f"New files: {sorted(added)}")
    if removed:
        messages.append(f"Removed files: {sorted(removed)}")
    if changed:
        messages.append(f"Changed files: {sorted(changed)}")

    assert not messages, (
        "Generated models are out of date. Differences found:\n"
        + "\n".join(messages)
        + "\n\nRun 'hatch run scripts:generate-schemas' for the affected schema(s) "
        "and commit the result."
    )


def _extract_class_blocks(source: str) -> str:
    """Extract everything from the first class definition onward.

    Single-schema generation may produce fewer re-export imports in shared
    modules (only types referenced by that technique), but the actual class
    definitions must be identical.  Comparing from the first ``class`` line
    ignores the variable import header.
    """
    match = re.search(r"^(class |@dataclass)", source, re.MULTILINE)
    return source[match.start() :] if match else source


@pytest.mark.long
def test_single_schema_generation_is_idempotent(tmp_path: Path) -> None:
    """Generating a single schema into a temp dir must match committed models.

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
    url = rec_technique_urls[0]

    generate_models(url, output_dir=tmp_path)

    for generated_file in sorted(tmp_path.rglob("*.py")):
        rel = generated_file.relative_to(tmp_path)
        committed = DEFAULT_MODEL_OUTPUT_DIR / rel
        assert committed.exists(), f"Unexpected file generated: {rel}"
        generated = generated_file.read_text(encoding="utf-8")
        expected = committed.read_text(encoding="utf-8")
        assert _extract_class_blocks(generated) == _extract_class_blocks(expected), (
            f"Single-schema generation produced different output for {rel}. "
            "Shared modules may be affected by which schemas are included in the run."
        )
