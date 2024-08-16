from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from itertools import zip_longest
from pathlib import Path
import shutil

PathType = Path | str


def _files_equal(path1: PathType, path2: PathType) -> bool:
    with open(str(path1)) as file1, open(str(path2)) as file2:
        for line1, line2 in zip_longest(file1, file2, fillvalue=""):
            if line1 != line2 and not line1.startswith("#   timestamp:"):
                return False
    return True


def _get_backup_path(path: PathType) -> Path:
    _path = Path(path)
    return Path(_path.parent, f".{_path.stem}.bak{_path.suffix}")


def get_original_path(path: PathType) -> Path:
    original_path = str(path)
    if original_path.startswith("."):
        original_path = original_path[1:]
    return Path(original_path.replace(".bak", ""))


def is_file_changed(path: PathType) -> bool:
    other_path = _get_backup_path(path)
    if other_path.exists():
        return not _files_equal(path, other_path)
    return True


def _backup_file(path: PathType) -> Path:
    backup_path = _get_backup_path(path)
    if Path(path).exists():
        shutil.copyfile(path, str(backup_path))
    return backup_path


def restore_backup(path: PathType) -> None:
    backup_path = _get_backup_path(path)
    if backup_path.exists():
        backup_path.replace(path)


def is_backup_file(path: PathType) -> bool:
    return ".bak" in Path(path).suffixes


@contextmanager
def backup_paths(
    paths: Sequence[PathType], *, restore: bool | None = False
) -> Iterator[list[Path]]:
    backup_paths = [_backup_file(path) for path in paths]
    try:
        yield backup_paths
    except Exception:
        for path in paths:
            _get_backup_path(path).unlink(missing_ok=True)
        raise

    if not restore:
        for path in paths:
            shutil.copyfile(_get_backup_path(path), str(path))
    for path in paths:
        _get_backup_path(path).unlink(missing_ok=True)


@contextmanager
def backup(path: PathType, *, restore: bool | None = False) -> Iterator[Path]:
    with backup_paths([path], restore=restore) as working_path:
        yield working_path[0]
