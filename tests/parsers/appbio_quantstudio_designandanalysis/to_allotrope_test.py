from allotropy.parser_factory import Vendor
from tests.to_allotrope_test import ParserTest

"""
NOTES ON INVALID FILES

- Files without a standard experiment type are not supported
    appbio_quantstudio_designandanalysis_QS7Pro_Multiplex_example08

- Files with open array structure are not supported at the moment
    appbio_quantstudio_designandanalysis_QS7Pro_Standard_Curve_TAC_example15
    appbio_quantstudio_designandanalysis_OpenArray_GeneExp_example16
    appbio_quantstudio_designandanalysis_OpenArray_Genotyping_example17

- example.xlsx
    TODO(nstender): figure out where this came from, and why it errors.
"""


class TestParser(ParserTest):
    VENDOR = Vendor.APPBIO_QUANTSTUDIO_DESIGNANDANALYSIS
