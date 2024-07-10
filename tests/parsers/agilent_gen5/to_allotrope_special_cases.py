from allotropy.parser_factory import Vendor
from allotropy.testing.utils import (
    from_file,
    validate_contents,
)


def test_to_allotrope_absorbance_no_pm_in_time() -> None:
    test_filepath = "tests/parsers/agilent_gen5/testdata/absorbance/exclude/endpoint_pathlength_correct_singleplate_no_pm_in_time.txt"
    expected_filepath = "tests/parsers/agilent_gen5/testdata/absorbance/endpoint_pathlength_correct_singleplate.json"
    allotrope_dict = from_file(test_filepath, Vendor.AGILENT_GEN5)

    allotrope_dict["plate reader aggregate document"]["data system document"][
        "file name"
    ] = "endpoint_pathlength_correct_singleplate.txt"

    validate_contents(allotrope_dict, expected_filepath)
