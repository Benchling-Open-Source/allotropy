from pathlib import Path

import pytest

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_vi_cell_blu.vi_cell_blu_reader import ViCellBluReader

TESTDATA = Path(__file__).parent / "testdata"


@pytest.mark.parametrize(
    "file_name,old_id,new_id,expected_first_id",
    [
        # Summary export where every sample ID is numeric with leading zeros.
        ("Beckman_Vi-Cell-BLU_example01.csv", "CLB", "00", "00001"),
        # Detail export with a single sample.
        ("Beckman_Vi-Cell-BLU_detail_export.csv", "20-7", "00123", "00123"),
    ],
)
def test_read_keeps_leading_zeros_in_sample_id(
    file_name: str, old_id: str, new_id: str, expected_first_id: str
) -> None:
    contents = (TESTDATA / file_name).read_text(encoding="utf-8")
    assert old_id in contents
    named_file_contents = NamedFileContents(
        contents=contents.replace(old_id, new_id).encode(),
        original_file_path=file_name,
    )
    data = ViCellBluReader.read(named_file_contents)
    assert data["Sample ID"].iloc[0] == expected_first_id
