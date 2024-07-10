import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

VENDOR_TYPE = Vendor.MOLDEV_SOFTMAX_PRO


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
