import inspect
from pathlib import Path

import pytest


# ParserTest will ignore any files with "error" or "exclude" in their paths.
def _is_valid_testcase(path: Path) -> bool:
    if not path.is_file():
        return False
    if "error" in str(path) or "exclude" in str(path):
        return False
    return path.suffix.lower() != ".json"


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    # Only parametrize test_file_path if class variable VENDOR is defined, signifying a ParserTest
    if "test_file_path" in metafunc.fixturenames and metafunc.cls.VENDOR:
        testdata_dir = Path(Path(inspect.getfile(metafunc.cls)).parent, "testdata")
        paths = [path for path in testdata_dir.rglob("*") if _is_valid_testcase(path)]
        ids = [str(path.relative_to(testdata_dir)) for path in paths]
        metafunc.parametrize("test_file_path", paths, ids=ids)
