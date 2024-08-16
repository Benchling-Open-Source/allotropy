from pathlib import Path

import pytest

from allotropy.allotrope.schema_parser.generate_schemas import generate_schemas
from allotropy.allotrope.schema_parser.path_util import (
    get_rel_schema_path,
    SCHEMA_DIR_PATH,
)


@pytest.mark.parametrize(
    "schema_path",
    [path for path in [get_rel_schema_path(path) for path in Path(SCHEMA_DIR_PATH).rglob("*.json")] if len(path.parts) == 6]
)
def test_generate_schemas_runs_to_completion(schema_path: Path) -> None:
    models_changed = generate_schemas(dry_run=True, schema_regex=str(schema_path))
    assert (
        not models_changed
    ), f"Expected no models files to have changed by generate-schemas script, found changes in: {models_changed}.\nPlease run 'hatch run scripts:generate-schemas' and validate the changes."
