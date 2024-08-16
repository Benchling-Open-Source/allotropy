from pathlib import Path

import pytest

from allotropy.allotrope.schema_parser.backup_manager import (
    _get_backup_path,
    get_original_path,
)


@pytest.mark.parametrize(
    "path",
    [
        "test.py",
        "directory/nested/test.py",
        "weird_extension.tmp.blah.py",
    ]
)
def test_get_backup_path(path: str) -> None:
    backup_path = _get_backup_path(path)
    assert backup_path.name.startswith(".")
    assert backup_path.name.endswith(".bak.py")
    assert get_original_path(backup_path) == Path(path)
