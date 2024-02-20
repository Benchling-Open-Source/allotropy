# import json

import pytest

# from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import Model
from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents

"""from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_parser import (
    AppBioQuantStudioDesignandanalysisParser,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_structure import (
    Data,
)
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from tests.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_data import (
    get_broken_calc_doc_data,
    get_broken_calc_doc_model,
    get_data,
    get_data2,
    get_genotyping_data,
    get_genotyping_model,
    get_model,
    get_model2,
    get_rel_std_curve_data,
    get_rel_std_curve_model,
)"""

OUTPUT_FILES = ("appbio_quantstudio_designandanalysis_example_01",)

VENDOR_TYPE = Vendor.APPBIO_QUANTSTUDIO_DESIGNANDANALYSIS


# @pytest.mark.parametrize("output_file", OUTPUT_FILES)
# def test_parse_appbio_quantstudio_to_asm_schema(output_file: str) -> None:
#     test_filepath = f"tests/parsers/appbio_quantstudio_designandanalysis/testdata/{output_file}.xlsx"
#     allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
#
#     # start: make a JSON
#     target_filename = output_file.replace(".xlsx", ".json")
#     with open(
#         f"tests/parsers/appbio_quantstudio_designandanalysis/testdata/{target_filename}.json",
#         "w",
#     ) as fp:
#         json.dump(allotrope_dict, fp)
#     # end: make a JSON
#
#     validate_schema(allotrope_dict, "pcr/BENCHLING/2023/09/qpcr.json")


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_appbio_quantstudio_to_asm_contents(output_file: str) -> None:
    test_filepath = f"tests/parsers/appbio_quantstudio_designandanalysis/testdata/{output_file}.xlsx"
    expected_filepath = test_filepath.replace(".xlsx", ".json")
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_contents(allotrope_dict, expected_filepath)


"""@pytest.mark.short
@pytest.mark.parametrize(
    "file_name,data,model",
    [
        ("appbio_quantstudio_test01.txt", get_data(), get_model()),
        ("appbio_quantstudio_test02.txt", get_data2(), get_model2()),
        (
            "appbio_quantstudio_test03.txt",
            get_genotyping_data(),
            get_genotyping_model(),
        ),
        (
            "appbio_quantstudio_test04.txt",
            get_rel_std_curve_data(),
            get_rel_std_curve_model(),
        ),
        # test 5 will check the calculated data document structure when an
        # expected value is missing. In this case a path is borken and should
        # be entirely removed.
        (
            "appbio_quantstudio_test05.txt",
            get_broken_calc_doc_data(),
            get_broken_calc_doc_model(),
        ),
    ],
)
def test_get_model(file_name: str, data: Data, model: Model) -> None:
    parser = AppBioQuantStudioDesignandanalysisParser(TimestampParser())
    generated = parser._get_model(data, file_name)
    assert generated == model
"""
