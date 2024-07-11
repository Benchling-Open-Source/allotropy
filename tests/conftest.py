import inspect
from pathlib import Path

import pytest

# ParserTest will ignore any files with "error",  "exclude", or "invalid" in their path.
EXCLUDE_KEYWORDS = {"error", "exclude", "invalid"}


def _is_valid_testcase(path: Path) -> bool:
    if not path.is_file():
        return False
    if str(path.stem).startswith("."):
        return False
    if path.suffix.lower() == ".json":
        return False
    return all(keyword not in str(path).lower() for keyword in EXCLUDE_KEYWORDS)


def get_test_cases(testdata_dir: Path) -> list[Path]:
    return [path for path in testdata_dir.rglob("*") if _is_valid_testcase(path)]


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    # Only parametrize test_file_path if class variable VENDOR is defined, signifying a ParserTest
    if "test_file_path" in metafunc.fixturenames and metafunc.cls.VENDOR:
        testdata_dir = Path(Path(inspect.getfile(metafunc.cls)).parent, "testdata")
        paths = get_test_cases(testdata_dir)
        ids = [str(path.relative_to(testdata_dir)) for path in paths]
        metafunc.parametrize("test_file_path", paths, ids=ids)
