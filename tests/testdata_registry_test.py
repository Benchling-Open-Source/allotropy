from pathlib import Path

from allotropy_testdata import registry
import pytest


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(registry, "_DATA_DIR", tmp_path)
    return tmp_path


def _touch(*paths: Path) -> None:
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")


def test_pairs_input_with_json_next_to_it(data_dir: Path) -> None:
    testdata = data_dir / "vendor_a" / "testdata"
    _touch(
        testdata / "example01.txt",
        testdata / "example01.json",
        testdata / "no_output.txt",
    )

    assert registry.get_input_files("vendor_a") == [
        testdata / "example01.txt",
        testdata / "no_output.txt",
    ]
    assert registry.get_test_files("vendor_a") == {
        testdata / "example01.txt": testdata / "example01.json"
    }
    assert registry.get_output_files("vendor_a") == [testdata / "example01.json"]


def test_json_input_in_input_folder_pairs_with_output_folder(data_dir: Path) -> None:
    testdata = data_dir / "json_vendor" / "testdata"
    _touch(
        testdata / "input" / "run1.json",
        testdata / "output" / "run1.json",
        testdata / "input" / "run2.json",
    )

    assert registry.get_input_files("json_vendor") == [
        testdata / "input" / "run1.json",
        testdata / "input" / "run2.json",
    ]
    assert registry.get_test_files("json_vendor") == {
        testdata / "input" / "run1.json": testdata / "output" / "run1.json"
    }
    assert registry.get_output_files("json_vendor") == [
        testdata / "output" / "run1.json"
    ]


def test_json_outside_input_folder_is_not_an_input(data_dir: Path) -> None:
    testdata = data_dir / "vendor_a" / "testdata"
    _touch(testdata / "example01.csv", testdata / "example01.json")

    assert registry.get_input_files("vendor_a") == [testdata / "example01.csv"]


def test_nested_folders_are_searched(data_dir: Path) -> None:
    testdata = data_dir / "vendor_a" / "testdata"
    _touch(testdata / "v2" / "example.txt", testdata / "v2" / "example.json")

    assert registry.get_test_files("vendor_a") == {
        testdata / "v2" / "example.txt": testdata / "v2" / "example.json"
    }


@pytest.mark.parametrize("folder", ["errors", "exclude", "invalid"])
def test_negative_case_folders_are_not_inputs(data_dir: Path, folder: str) -> None:
    testdata = data_dir / "vendor_a" / "testdata"
    _touch(testdata / folder / "bad.txt", testdata / "good.txt")

    assert registry.get_input_files("vendor_a") == [testdata / "good.txt"]
    assert registry.get_file("vendor_a", f"{folder}/bad.txt").is_file()


def test_rslt_folder_is_a_single_input(data_dir: Path) -> None:
    testdata = data_dir / "vendor_a" / "testdata"
    _touch(testdata / "run.rslt" / "inner.dat", testdata / "run.json")

    assert registry.get_test_files("vendor_a") == {
        testdata / "run.rslt": testdata / "run.json"
    }


def test_unknown_vendor_raises(data_dir: Path) -> None:
    _touch(data_dir / "vendor_a" / "testdata" / "a.txt")

    with pytest.raises(ValueError, match="not found"):
        registry.get_vendor_dir("missing")


def test_list_vendors_requires_testdata_folder(data_dir: Path) -> None:
    _touch(data_dir / "vendor_a" / "testdata" / "a.txt", data_dir / "empty" / "x.py")

    assert registry.list_vendors() == ["vendor_a"]


def test_repo_json_input_vendor_pairs_every_input() -> None:
    pairs = registry.get_test_files("benchling_chromeleon")

    assert pairs
    for input_file, output_file in pairs.items():
        assert input_file.parent.name == "input"
        assert input_file.suffix == ".json"
        assert output_file == input_file.parent.parent / "output" / input_file.name


def test_repo_vendors_pair_like_parser_tests() -> None:
    for vendor in registry.list_vendors():
        inputs = registry.get_input_files(vendor)
        pairs = registry.get_test_files(vendor)
        assert set(pairs) <= set(inputs)
        assert all(output.is_file() for output in pairs.values())
