import pytest

from allotropy.parser_factory import Vendor
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_parser import (
    AppBioQuantStudioParser,
)
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from tests.parsers.appbio_quantstudio.appbio_quantstudio_data import (
    get_data,
    get_data2,
    get_genotyping_data,
    get_genotyping_model,
    get_model,
    get_model2,
)
from tests.parsers.test_utils import from_file, validate_contents, validate_schema

output_files = (
    "appbio_quantstudio_example01",
    "appbio_quantstudio_example02",
    "appbio_quantstudio_example03",
)

VENDOR_TYPE = Vendor.APPBIO_QUANTSTUDIO


@pytest.mark.parametrize("output_file", output_files)
def test_parse_appbio_quantstudio_to_asm_schema(output_file: str) -> None:
    test_filepath = f"tests/parsers/appbio_quantstudio/testdata/{output_file}.txt"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_schema(allotrope_dict, "pcr/BENCHLING/2023/09/qpcr.json")


@pytest.mark.parametrize("output_file", output_files)
def test_parse_appbio_quantstudio_to_asm_contents(output_file: str) -> None:
    test_filepath = f"tests/parsers/appbio_quantstudio/testdata/{output_file}.txt"
    expected_filepath = test_filepath.replace(".txt", ".json")
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_contents(allotrope_dict, expected_filepath)


@pytest.mark.short
def test_get_model() -> None:
    parser = AppBioQuantStudioParser(TimestampParser())
    model = parser._get_model(get_data(), "appbio_quantstudio_test01.txt")

    assert model.qPCR_aggregate_document is not None
    for qpcr_doc in model.qPCR_aggregate_document.qPCR_document:
        for (
            measurement_doc
        ) in qpcr_doc.measurement_aggregate_document.measurement_document:
            measurement_doc.measurement_identifier = ""

    assert model == get_model()

    model = parser._get_model(get_data2(), "appbio_quantstudio_test02.txt")

    assert model.qPCR_aggregate_document is not None
    for qpcr_doc in model.qPCR_aggregate_document.qPCR_document:
        for (
            measurement_doc
        ) in qpcr_doc.measurement_aggregate_document.measurement_document:
            measurement_doc.measurement_identifier = ""

    assert model == get_model2()


@pytest.mark.short
def test_get_genotyping_model() -> None:
    parser = AppBioQuantStudioParser(TimestampParser())
    model = parser._get_model(get_genotyping_data(), "appbio_quantstudio_test03.txt")

    assert model.qPCR_aggregate_document is not None
    for qpcr_doc in model.qPCR_aggregate_document.qPCR_document:
        for (
            measurement_doc
        ) in qpcr_doc.measurement_aggregate_document.measurement_document:
            measurement_doc.measurement_identifier = ""

    assert model == get_genotyping_model()
