import pytest

from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import Model
from allotropy.parser_factory import Vendor
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_parser import (
    AppBioQuantStudioParser,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import Data
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from tests.parsers.appbio_quantstudio.appbio_quantstudio_data import (
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
)
from tests.parsers.test_utils import from_file, validate_contents

OUTPUT_FILES = (
    "appbio_quantstudio_example01",
    "appbio_quantstudio_example02",
    "appbio_quantstudio_example03",
    "appbio_quantstudio_example04",
    "appbio_quantstudio_example05",
    "appbio_quantstudio_example06",
    "appbio_quantstudio_example07",
    "appbio_quantstudio_example08",
    "appbio_quantstudio_multiple_cal_doc_wells",
)

VENDOR_TYPE = Vendor.APPBIO_QUANTSTUDIO


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_appbio_quantstudio_to_asm_contents(output_file: str) -> None:
    test_filepath = f"tests/parsers/appbio_quantstudio/testdata/{output_file}.txt"
    expected_filepath = test_filepath.replace(".txt", ".json")
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_contents(allotrope_dict, expected_filepath)


@pytest.mark.short
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
    parser = AppBioQuantStudioParser(TimestampParser())
    generated = parser._get_model(data, file_name)
    assert generated == model
