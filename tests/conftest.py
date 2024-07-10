import inspect
from pathlib import Path

import pytest


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    # Only parameterize test_file_path if class variable VENDOR is defined, signifying a ParserTest
    if "test_file_path" in metafunc.fixturenames and metafunc.cls.VENDOR:
        testdata_dir = Path(Path(inspect.getfile(metafunc.cls)).parent, "testdata")
        paths = [path for path in testdata_dir.rglob("*") if path.suffix.lower() != ".json"]
        metafunc.parametrize("test_file_path", paths)
