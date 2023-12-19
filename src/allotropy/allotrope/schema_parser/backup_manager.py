from contextlib import contextmanager
import os
import shutil
from typing import Optional, Union


def files_equal(path1: str, path2: str) -> bool:
    with open(path1) as file1, open(path2) as file2:
        for line1, line2 in zip(file1, file2):
            if line1 != line2 and not line1.startswith("#   timestamp:"):
                return False
    return True


def _get_backup_path(path: str) -> str:
    return f"{path}.bak"


def is_file_changed(path: str):
    if os.path.exists(_get_backup_path(path)):
        return not files_equal(path, _get_backup_path(path))
    return True


def _backup_file(path: str):
    if os.path.exists(path):
        shutil.copyfile(path, _get_backup_path(path))


def restore_backup(path: str):
    if os.path.exists(_get_backup_path(path)):
        os.rename(_get_backup_path(path), path)


def _remove_backup(path: str):
    if os.path.exists(_get_backup_path(path)):
        os.remove(_get_backup_path(path))


@contextmanager
def backup(paths: Union[list[str], str], restore: Optional[bool] = False):
    paths = paths if isinstance(paths, list) else [paths]
    [_backup_file(path) for path in paths]
    try:
        yield
    except Exception:
        [restore_backup(path) for path in paths]
        raise

    if restore:
        [restore_backup(path) for path in paths]
    else:
        [_remove_backup(path) for path in paths]
