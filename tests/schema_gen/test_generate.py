"""Test that generated models are up-to-date with cached schemas.

Running schema generation on all cached schemas must produce identical output
to what is already committed. If this test fails, run:

    hatch run scripts:generate-schemas <url>

for the affected schema(s) and commit the result.
"""

from __future__ import annotations

import hashlib

import pytest

from allotropy.allotrope.path_util import SCHEMA_DIR_PATH
from allotropy.schema_gen.generate import generate_models
from allotropy.schema_gen.naming import ALLOTROPE_URL_PREFIX, DEFAULT_MODEL_OUTPUT_DIR


def _collect_technique_schema_urls() -> list[str]:
    """Collect canonical URLs for all technique schemas (not core/qudt)."""
    urls: list[str] = []
    for f in sorted(SCHEMA_DIR_PATH.rglob("*.schema.json")):
        # Skip .embed. / .tabular. cache copies
        if ".embed." in f.name or ".tabular." in f.name:
            continue
        rel = f.relative_to(SCHEMA_DIR_PATH)
        # Skip core and qudt — pulled automatically as dependencies
        technique = rel.parts[1] if len(rel.parts) > 1 else ""
        if technique in ("core", "qudt"):
            continue
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

    urls = _collect_technique_schema_urls()
    assert urls, "No technique schemas found — check SCHEMA_DIR_PATH"

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
