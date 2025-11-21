from pathlib import Path
import re

import pytest

from allotropy.allotrope.schema_parser.generate_schemas import generate_schemas
from allotropy.allotrope.schema_parser.path_util import (
    get_rel_schema_path,
    SCHEMA_DIR_PATH,
)


def _get_schema_paths() -> list[Path]:
    return [
        path
        for path in [
            get_rel_schema_path(path) for path in Path(SCHEMA_DIR_PATH).rglob("*.json")
        ]
        if len(path.parts) == 6
    ]


def _pick_subset(paths: list[Path], count: int = 8) -> list[Path]:
    if not paths:
        return []
    if len(paths) <= count:
        return paths
    step = max(1, len(paths) // count)
    # Evenly sample across the set for broad coverage
    return [paths[i] for i in range(0, len(paths), step)][:count]


def test_generate_schemas_smoke_subset() -> None:
    """Fast smoke test over a representative subset of schemas."""
    paths = _get_schema_paths()
    subset = _pick_subset(paths, count=8)
    # Build a regex that matches exactly any of the chosen relative schema paths
    escaped = [re.escape(str(p)) for p in subset]
    pattern = rf"^({'|'.join(escaped)})$"
    models_changed = generate_schemas(dry_run=True, schema_regex=pattern)
    assert (
        not models_changed
    ), f"Expected no models files to have changed by generate-schemas script, found changes in: {models_changed}.\nPlease run 'hatch run scripts:generate-schemas' and validate the changes."


@pytest.mark.long
def test_generate_schemas_runs_to_completion() -> None:
    """Full run once across all schemas. Marked long for optional execution."""
    models_changed = generate_schemas(dry_run=True)
    assert (
        not models_changed
    ), f"Expected no models files to have changed by generate-schemas script, found changes in: {models_changed}.\nPlease run 'hatch run scripts:generate-schemas' and validate the changes."
