from pathlib import Path

from allotropy.allotrope.schema_parser.path_util import SCHEMA_DIR_PATH


def test_custom_schemas_have_changenotes() -> None:
    for file in Path(SCHEMA_DIR_PATH).glob("**/*.json"):
        if "shared" in str(file):
            continue
        if "BENCHLING" in str(file):
            assert Path(file.parent, "CHANGE_NOTES.md").exists()
