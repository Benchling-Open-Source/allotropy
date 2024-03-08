import re

import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents

VENDOR_TYPE = Vendor.MOLDEV_SOFTMAX_PRO
SCHEMA_FILE = "plate-reader/BENCHLING/2023/09/plate-reader.json"


@pytest.mark.parametrize(
    "file_name",
    [
        "abs_endpoint_plates",
        "MD_SMP_absorbance_endpoint_example01",
        "MD_SMP_absorbance_endpoint_example02",
        "MD_SMP_absorbance_endpoint_example04",
        "MD_SMP_absorbance_endpoint_example05",
        "MD_SMP_fluorescence_endpoint_example07",
        "MD_SMP_fluorescence_endpoint_example06",
        "MD_SMP_luminescence_endpoint_example03",
        "MD_SMP_luminescence_endpoint_example08",
        "MD_SMP_luminescence_endpoint_example09",
        "MD_SMP_absorbance_endpoint_partial_plate_example01",
        "MD_SMP_absorbance_endpoint_partial_plate_example02",
        "MD_SMP_absorbance_endpoint_partial_plate_example03",
        "MD_SMP_absorbance_endpoint_partial_plate_example04",
        "MD_SMP_absorbance_endpoint_partial_plate_example05",
        "MD_SMP_fluorescence_endpoint_partial_plate_example01",
        "MD_SMP_fluorescence_endpoint_partial_plate_example02",
        "MD_SMP_luminescence_endpoint_partial_plate_example01",
        "MD_SMP_luminescence_endpoint_partial_plate_example02",
        "group_cols_with_int_sample_names",
        "softmaxpro_no_calc_docs",
    ],
)
def test_to_allotrope(file_name: str) -> None:
    test_file = f"tests/parsers/moldev_softmax_pro/testdata/{file_name}.txt"
    expected_file = f"tests/parsers/moldev_softmax_pro/testdata/{file_name}.json"
    allotrope_dict = from_file(test_file, VENDOR_TYPE, CHARDET_ENCODING)
    validate_contents(allotrope_dict, expected_file)


def test_handles_unrecognized_read_mode() -> None:
    with pytest.raises(
        AllotropeConversionError,
        match=re.escape(
            "Unrecognized read mode: 'Time Resolved'. Only ['Absorbance', 'Fluorescence', 'Luminescence'] are supported."
        ),
    ):
        from_file(
            "tests/parsers/moldev_softmax_pro/testdata/trf_well_scan_plates.txt",
            VENDOR_TYPE,
        )


@pytest.mark.parametrize(
    "test_file",
    [
        "tests/parsers/moldev_softmax_pro/testdata/fl_kinetic_plates.txt",
        "tests/parsers/moldev_softmax_pro/testdata/lum_spectrum_columns.txt",
    ],
)
def test_unrecognized_read_type(test_file: str) -> None:
    with pytest.raises(
        AllotropeConversionError,
        match="Only Endpoint measurements can be processed at this time.",
    ):
        from_file(test_file, VENDOR_TYPE)


@pytest.mark.parametrize(
    "file_name",
    [
        "abs_endpoint_plates",
        "MD_SMP_absorbance_endpoint_example01",
        "MD_SMP_absorbance_endpoint_example02",
        "MD_SMP_absorbance_endpoint_example04",
        "MD_SMP_absorbance_endpoint_example05",
        "MD_SMP_fluorescence_endpoint_example07",
        "MD_SMP_fluorescence_endpoint_example06",
        "MD_SMP_luminescence_endpoint_example03",
        "MD_SMP_luminescence_endpoint_example08",
        "MD_SMP_luminescence_endpoint_example09",
        "MD_SMP_absorbance_endpoint_partial_plate_example01",
        "MD_SMP_absorbance_endpoint_partial_plate_example02",
        "MD_SMP_absorbance_endpoint_partial_plate_example03",
        "MD_SMP_absorbance_endpoint_partial_plate_example04",
        "MD_SMP_absorbance_endpoint_partial_plate_example05",
        "MD_SMP_fluorescence_endpoint_partial_plate_example01",
        "MD_SMP_fluorescence_endpoint_partial_plate_example02",
        "MD_SMP_luminescence_endpoint_partial_plate_example01",
        "MD_SMP_luminescence_endpoint_partial_plate_example02",
        "group_cols_with_int_sample_names",
        "softmaxpro_no_calc_docs",
    ],
)
def test_data_source_id_references(
    file_name: str,
) -> None:
    test_filepath = f"tests/parsers/moldev_softmax_pro/testdata/{file_name}.txt"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE, CHARDET_ENCODING)
    data_source_ids = []
    if (
        "calculated data aggregate document"
        in allotrope_dict["plate reader aggregate document"]
    ):
        data_source_ids = [
            dsd["data source identifier"]
            for calc_doc in allotrope_dict["plate reader aggregate document"][
                "calculated data aggregate document"
            ]["calculated data document"]
            for dsd in calc_doc["data source aggregate document"][
                "data source document"
            ]
        ]
    measurement_ids = [
        meas_doc["measurement identifier"]
        for spec_doc in allotrope_dict["plate reader aggregate document"][
            "plate reader document"
        ]
        for meas_doc in spec_doc["measurement aggregate document"][
            "measurement document"
        ]
    ]

    for data_source_id in data_source_ids:
        assert (
            data_source_id in measurement_ids
        ), f"data source identifier {data_source_id} is referenced but is not found in any measurement document"
