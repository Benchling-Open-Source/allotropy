from contextlib import contextmanager
from pathlib import Path
import shutil
from typing import Optional, Union

PathType = Union[Path, str]


def files_equal(path1: PathType, path2: PathType) -> bool:
    with open(str(path1)) as file1, open(str(path2)) as file2:
        for line1, line2 in zip(file1, file2):
            if line1 != line2 and not line1.startswith("#   timestamp:"):
                return False
    return True


def _get_backup_path(path: PathType) -> Path:
    _path = Path(path)
    return Path(_path.parent, f".{_path.stem}.bak{_path.suffix}")


def is_file_changed(path: PathType):
    if _get_backup_path(path).exists():
        return not files_equal(path, _get_backup_path(path))
    return True


def _backup_file(path: PathType):
    if Path(path).exists():
        shutil.copyfile(path, str(_get_backup_path(path)))


def restore_backup(path: PathType):
    if _get_backup_path(path).exists():
        _get_backup_path(path).rename(path)


def _remove_backup(path: PathType):
    _get_backup_path(path).unlink(missing_ok=True)


@contextmanager
def backup(paths: Union[list[PathType], PathType], *, restore: Optional[bool] = False):
    paths = paths if isinstance(paths, list) else [paths]
    [_backup_file(path) for path in paths]
    try:
        yield
    except Exception:
        # [restore_backup(path) for path in paths]
        raise

    if restore:
        [restore_backup(path) for path in paths]
    else:
        [_remove_backup(path) for path in paths]
