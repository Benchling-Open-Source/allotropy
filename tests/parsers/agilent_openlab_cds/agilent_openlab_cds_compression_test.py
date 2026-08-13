"""Tests that OpenLab CDS result sets are accepted at any level of compression.

OpenLab CDS exports a .rslt result set folder, which reaches us compressed. Users may compress it a
second time (e.g. right-click > Compress) and may keep either the .zip or the .rslt extension, so
all of those shapes must produce the same ASM.
"""
from pathlib import Path
from typing import Any
import zipfile

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parser_factory import Vendor
from allotropy.parsers.agilent_openlab_cds.agilent_openlab_cds_parser import (
    AgilentOpenLabCDSParser,
)
from allotropy.testing.utils import from_file
from allotropy.to_allotrope import allotrope_from_file, vendor_from_file

VENDOR = Vendor.AGILENT_OPENLAB_CDS
TESTDATA = Path("tests/parsers/agilent_openlab_cds/testdata")
RESULT_SET = TESTDATA / "Luxo HPLC-2023-09-01 07-52-44-04-00.rslt"
# Fields that legitimately differ between copies of the same result set.
FILE_PATH_FIELDS = {"file name", "UNC path"}


def _recompress(result_set: Path, output: Path, *, flatten: bool) -> Path:
    """Recompress the members of a result set archive, mimicking compressing the .rslt folder.

    With flatten, members land at the archive root, as when compressing the folder's contents.
    """
    with zipfile.ZipFile(result_set) as source, zipfile.ZipFile(
        output, "w", zipfile.ZIP_DEFLATED
    ) as dest:
        for name in source.namelist():
            if name.endswith("/") or Path(name).name.startswith("."):
                continue
            dest.writestr(Path(name).name if flatten else name, source.read(name))
    return output


def _nest(result_set: Path, output: Path) -> Path:
    """Compress the result set archive as a whole, mimicking compressing the .rslt file itself."""
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as dest:
        dest.write(result_set, result_set.name)
    return output


@pytest.fixture(scope="module")
def variants(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Every compression shape a user might upload, keyed by a description of how it was made."""
    tmp_path = tmp_path_factory.mktemp("openlab_cds")
    variants = {}
    for extension in ("zip", "rslt"):
        variants[f"folder compressed as .{extension}"] = _recompress(
            RESULT_SET, tmp_path / f"folder.{extension}", flatten=False
        )
        variants[f"folder contents compressed as .{extension}"] = _recompress(
            RESULT_SET, tmp_path / f"contents.{extension}", flatten=True
        )
        variants[f"result set archive compressed as .{extension}"] = _nest(
            RESULT_SET, tmp_path / f"nested.{extension}"
        )
    return variants


@pytest.fixture(scope="module")
def expected() -> dict[str, Any]:
    return from_file(RESULT_SET, VENDOR)


def _without_file_paths(asm: Any) -> Any:
    if isinstance(asm, dict):
        return {
            key: "<file path>"
            if key in FILE_PATH_FIELDS
            else _without_file_paths(value)
            for key, value in asm.items()
        }
    if isinstance(asm, list):
        return [_without_file_paths(item) for item in asm]
    return asm


@pytest.mark.long
@pytest.mark.parametrize(
    "variant",
    [
        "folder compressed as .zip",
        "folder contents compressed as .zip",
        "result set archive compressed as .zip",
        "folder compressed as .rslt",
        "folder contents compressed as .rslt",
        "result set archive compressed as .rslt",
    ],
)
def test_recompressed_result_set_matches_result_set(
    variant: str, variants: dict[str, Path], expected: dict[str, Any]
) -> None:
    actual = from_file(variants[variant], VENDOR)
    assert _without_file_paths(actual) == _without_file_paths(expected)


@pytest.mark.long
def test_discovers_vendor_for_zipped_result_set(variants: dict[str, Path]) -> None:
    assert vendor_from_file(str(variants["folder compressed as .zip"])) == VENDOR


def test_sniff_rejects_zip_of_other_vendor(tmp_path: Path) -> None:
    other_vendor_zip = tmp_path / "other.zip"
    with zipfile.ZipFile(other_vendor_zip, "w") as zip_ref:
        zip_ref.writestr("run_summary.csv", "Well,Sample\nA1,foo\n")
    with open(other_vendor_zip, "rb") as contents:
        assert not AgilentOpenLabCDSParser.sniff(
            NamedFileContents(contents, str(other_vendor_zip))
        )


def test_raises_on_zip_without_result_set(tmp_path: Path) -> None:
    not_a_result_set = tmp_path / "not_a_result_set.zip"
    with zipfile.ZipFile(not_a_result_set, "w") as zip_ref:
        zip_ref.writestr("readme.txt", "no result set here")
    with pytest.raises(AllotropeConversionError, match="Could not find ACAML file"):
        allotrope_from_file(str(not_a_result_set), VENDOR)


def test_raises_on_file_that_is_not_compressed(tmp_path: Path) -> None:
    not_compressed = tmp_path / "not_compressed.rslt"
    not_compressed.write_bytes(b"not a zip file")
    with pytest.raises(
        AllotropeConversionError, match="must be a compressed .rslt result set"
    ):
        allotrope_from_file(str(not_compressed), VENDOR)
