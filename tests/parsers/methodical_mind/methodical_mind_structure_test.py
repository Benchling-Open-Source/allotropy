import numpy as np
import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.methodical_mind.methodical_mind_structure import (
    CombinedData,
    PlateData,
)


def test_create_combined_data() -> None:
    with open(
        "tests/parsers/methodical_mind/testdata/methodical_test_1.txt"
    ) as test_file:
        named_file_contents = NamedFileContents(
            contents=test_file, original_file_name="original"
        )
        file_lines = read_to_lines(named_file_contents)
        reader = CsvReader(file_lines)
        combined_data = CombinedData.create(reader)

    assert (
        combined_data.file_name
        == "Z:\\MSD-WP\\Export\\22M0TALA85_2023-09-08-133933.txt"
    )
    assert combined_data.version == "MMPR 1.0.38"
    assert combined_data.model == "HTS"
    assert combined_data.serial_number == "1298873245"
    assert combined_data.plate_doc_info[0].plate_well_count == 96
    assert len(combined_data.plate_doc_info) == 2


def test_create_get_parameter() -> None:
    lines = [
        "FileName :\tZ:\\DC\\Export\\test_file.txt",
        "Version  :\tMMPR 1.0.38",
        "",
        "User     :\tJeffy P",
    ]
    reader = CsvReader(lines)
    assert CombinedData.get_parameter(reader, "User") == "Jeffy P"


def test_create_get_parameter_when_missing() -> None:
    lines = [
        "FileName :\tZ:\\DC\\Export\\test_file.txt",
        "Version  :\tMMPR 1.0.38",
        "",
        "User     :",
    ]
    reader = CsvReader(lines)
    assert CombinedData.get_parameter(reader, "User") is None


def test_create_plate_well_data() -> None:
    data = {
        "Unnamed: 0": ["A", np.nan, np.nan, np.nan, np.nan],
        "1": [8213, 3475, 5589, 2131, 761],
        "2": [8062, 2341, 3147, 1846, 67778],
        "3": [463, 1485, 15855, 9587, 3226],
        "4": [2181, 6665, 70504, 40572, 13664],
        "5": [839, 2692, 247, 128, 5024],
    }
    plate_df = pd.DataFrame(data)

    result = PlateData.create(plate_df, "2022-01-01", "Jeffy P", "WP002", 5)

    assert result.plate_well_count == 5
    assert len(result.well_data) == 25
    assert result.well_data[0].luminescence == 8213
    assert result.well_data[0].location_identifier == "A1_1"
    assert result.well_data[-1].location_identifier == "A5_5"
