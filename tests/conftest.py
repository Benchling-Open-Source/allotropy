import inspect
from pathlib import Path
import re
from typing import Any

import pytest
from pytest import FixtureRequest, Parser

from allotropy.testing.utils import get_testdata_dir

# ParserTest will ignore any files with "error",  "exclude", or "invalid" in their path.
EXCLUDE_KEYWORDS = {"error", "exclude", "invalid"}


def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        "--overwrite",
        action="store_true",
        help="If set, overwrite failing tests with new data.",
    )
    parser.addoption(
        "--exclude",
        action="store",
        default="",
        help="Comma separated list of patterns to exclude file paths from to_allotropy_test. If set, any test file matching one of the patterns will be excluded.",
    )
    parser.addoption(
        "--filter",
        action="store",
        default="",
        help="Comma separated list of patterns to filter file paths from to_allotropy_test. If set, only tests matching one of the patterns will be included.",
    )
    parser.addoption(
        "--warn_unread_keys",
        action="store_true",
        help="If set, show warning if any keys in a SeriesData are unread.",
    )


@pytest.fixture
def overwrite(request: FixtureRequest) -> Any:
    return request.config.getoption("--overwrite")


@pytest.fixture
def warn_unread_keys(request: FixtureRequest) -> Any:
    return request.config.getoption("--warn_unread_keys")


def _is_valid_testcase(path: Path) -> bool:
    if not path.is_file():
        return False
    if str(path.stem).startswith("."):
        return False
    if "__pycache__" in str(path):
        return False
    if path.suffix.lower() in (".pyc", ".py"):
        return False
    # Special case to be used when input files are json, test files are put in an input/ folder to indicate.
    if path.parts[-2] == "input":
        return True
    if path.suffix.lower() == ".json":
        return False
    return all(keyword not in str(path).lower() for keyword in EXCLUDE_KEYWORDS)


def get_test_cases(testdata_dir: Path) -> list[Path]:
    test_cases = []
    for path in testdata_dir.glob("*"):
        if path.is_dir() and path.suffix.lower() in (".rslt", ".d"):
            test_cases.append(path)
        elif path.is_file() and _is_valid_testcase(path):
            test_cases.append(path)
        elif path.is_dir():
            for subpath in path.rglob("*"):
                if subpath.is_file() and _is_valid_testcase(subpath):
                    test_cases.append(subpath)
    return test_cases


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    # Only parametrize test_file_path if class variable VENDOR is defined, signifying a ParserTest
    if "test_file_path" in metafunc.fixturenames and metafunc.cls.VENDOR:
        testdata_dir = get_testdata_dir(inspect.getfile(metafunc.cls))
        paths = get_test_cases(testdata_dir)
        if metafunc.config.option.filter:
            paths = [
                path
                for path in paths
                if any(
                    re.search(regex, str(path))
                    for regex in metafunc.config.option.filter.split(",")
                )
            ]
        if metafunc.config.option.exclude:
            paths = [
                path
                for path in paths
                if not any(
                    re.search(regex, str(path))
                    for regex in metafunc.config.option.exclude.split(",")
                )
            ]
        ids = [str(path.relative_to(testdata_dir)) for path in paths]
        metafunc.parametrize("test_file_path", paths, ids=ids)
