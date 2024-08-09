import pytest

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    Data,
    Mapper,
)
from allotropy.parser_factory import Vendor
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_parser import (
    AppBioQuantStudioParser,
)
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

VENDOR_TYPE = Vendor.APPBIO_QUANTSTUDIO


@pytest.mark.short
@pytest.mark.parametrize(
    "data,model",
    [
        (get_data("appbio_quantstudio_test01.txt"), get_model()),
        (get_data2("appbio_quantstudio_test02.txt"), get_model2()),
        (get_genotyping_data("appbio_quantstudio_test03.txt"), get_genotyping_model()),
        (
            get_rel_std_curve_data("appbio_quantstudio_test04.txt"),
            get_rel_std_curve_model(),
        ),
        # test 5 will check the calculated data document structure when an
        # expected value is missing. In this case a path is broken and should
        # be entirely removed.
        (
            get_broken_calc_doc_data("appbio_quantstudio_test05.txt"),
            get_broken_calc_doc_model(),
        ),
    ],
)
def test_get_model(data: Data, model: Model) -> None:
    parser = AppBioQuantStudioParser(TimestampParser())
    generated = parser._get_mapper(Mapper).map_model(data)
    assert generated == model
