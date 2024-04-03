import pytest

from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents

OUTPUT_FILES = (
    "appbio_quantstudio_designandanalysis_QS1_Standard_Curve_example01",
    "appbio_quantstudio_designandanalysis_QS3_Relative_Quantification_example02",
    "appbio_quantstudio_designandanalysis_QS5_Standard_Curve_4Plex_example03",
    "appbio_quantstudio_designandanalysis_QS6_Standard_Curve_example04",
    "appbio_quantstudio_designandanalysis_QS6Pro_Standard_Curve_example05",
    "appbio_quantstudio_designandanalysis_QS7_Standard_Curve_example06",
    # "appbio_quantstudio_designandanalysis_QS7Pro_Genotyping_example07",
    "appbio_quantstudio_designandanalysis_QS7Pro_Multiplex_example08",
    # "appbio_quantstudio_designandanalysis_QS7Pro_PCR_with_Melt_example09",
    # "appbio_quantstudio_designandanalysis_QS7Pro_Presence_and_Absence_example10",
    "appbio_quantstudio_designandanalysis_QS7Pro_Relative_Quantification_example11",
    "appbio_quantstudio_designandanalysis_QS7Pro_Relative_Quantification_Biogroup_example12",
    "appbio_quantstudio_designandanalysis_QS7Pro_Relative_Standard_Curve_example13",
    "appbio_quantstudio_designandanalysis_QS7Pro_Standard_Curve_example14",
    # "appbio_quantstudio_designandanalysis_QS7Pro_Standard_Curve_TAC_example15",
    # "appbio_quantstudio_designandanalysis_OpenArray_GeneExp_example16",
    # "appbio_quantstudio_designandanalysis_OpenArray_Genotyping_example17",
)

VENDOR_TYPE = Vendor.APPBIO_QUANTSTUDIO_DESIGNANDANALYSIS


@pytest.mark.design_quantstudio
@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_appbio_quantstudio_to_asm_contents(output_file: str) -> None:
    test_filepath = f"tests/parsers/appbio_quantstudio_designandanalysis/testdata/{output_file}.xlsx"
    expected_filepath = test_filepath.replace(".xlsx", ".json")
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_contents(allotrope_dict, expected_filepath)
