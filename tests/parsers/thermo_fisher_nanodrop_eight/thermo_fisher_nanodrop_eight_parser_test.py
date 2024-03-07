import pytest

from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents

OUTPUT_FILES = (
    "Thermo_NanoDrop_Eight_example01.txt",
    "Thermo_NanoDrop_Eight_example02.txt",
    "Thermo_NanoDrop_Eight_example03.txt",
    "Thermo_NanoDrop_Eight_example04.txt",
)

VENDOR_TYPE = Vendor.THERMO_FISHER_NANODROP_EIGHT


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_thermo_fisher_nanodrop_eight_to_asm_expected_contents(
    output_file: str,
) -> None:
    test_filepath = f"tests/parsers/thermo_fisher_nanodrop_eight/testdata/{output_file}"
    expected_filepath = (
        f"tests/parsers/thermo_fisher_nanodrop_eight/testdata/{output_file}".removesuffix(
            "txt"
        )
        + "json"
    )
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath)


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_thermo_fisher_nanodrop_eight_data_source_ids(
    output_file: str,
) -> None:
    test_filepath = f"tests/parsers/thermo_fisher_nanodrop_eight/testdata/{output_file}"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    data_source_ids = [
        dsd["data source identifier"]
        for calc_doc in allotrope_dict["spectrophotometry aggregate document"][
            "calculated data aggregate document"
        ]["calculated data document"]
        for dsd in calc_doc["data source aggregate document"]["data source document"]
    ]
    measurement_ids = [
        meas_doc["measurement identifier"]
        for spec_doc in allotrope_dict["spectrophotometry aggregate document"][
            "spectrophotometry document"
        ]
        for meas_doc in spec_doc["measurement aggregate document"][
            "measurement document"
        ]
    ]

    for data_source_id in data_source_ids:
        assert (
            data_source_id in measurement_ids
        ), f"data source identifier {data_source_id} is referenced but is not found in any measurement document"
