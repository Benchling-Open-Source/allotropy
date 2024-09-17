from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from itertools import zip_longest
from pathlib import Path
import shutil

from allotropy.parsers.utils.uuids import random_uuid_str

PathType = Path | str


def _files_equal(path1: PathType, path2: PathType) -> bool:
    with open(str(path1)) as file1, open(str(path2)) as file2:
        for line1, line2 in zip_longest(file1, file2, fillvalue=""):
            if line1 != line2 and not line1.startswith("#   timestamp:"):
                return False
    return True


def _get_backup_path(path: PathType) -> Path:
    _path = Path(path)
    return Path(_path.parent, f".{_path.stem}.{random_uuid_str()}.bak{_path.suffix}")


def get_original_path(path: PathType) -> Path:
    _path = Path(path)
    filename = _path.stem
    if filename.startswith("."):
        # Remove .<uuid>.bak from filename by removing two extensions (by calling .stem)
        filename = f"{Path(Path(filename[1:]).stem).stem}{_path.suffix}"
    return Path(_path.parent, filename)


def is_file_changed(path: PathType) -> bool:
    if is_backup_file(path):
        other_path = get_original_path(path)
    else:
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
    except (Exception, KeyboardInterrupt):
        for backup in backup_paths:
            backup.unlink(missing_ok=True)
        raise

    if not restore:
        for backup, original in zip(backup_paths, paths, strict=True):
            if is_file_changed(backup):
                shutil.copyfile(backup, str(original))
    for backup in backup_paths:
        backup.unlink(missing_ok=True)


@contextmanager
def backup(path: PathType, *, restore: bool | None = False) -> Iterator[Path]:
    with backup_paths([path], restore=restore) as working_path:
        yield working_path[0]
