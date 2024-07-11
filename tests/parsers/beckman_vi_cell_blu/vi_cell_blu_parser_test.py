from more_itertools import one

from allotropy.allotrope.models.adm.cell_counting.benchling._2023._11.cell_counting import (
    Model,
)
from allotropy.parsers.beckman_vi_cell_blu.vi_cell_blu_parser import ViCellBluParser
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from tests.parsers.beckman_vi_cell_blu.vi_cell_blu_data import (
    get_data,
    get_filename,
    get_model,
)


def _clear_measurement_identifier(model: Model) -> None:
    cell_counting_aggregate_document = model.cell_counting_aggregate_document
    assert cell_counting_aggregate_document

    cell_counting_document_item = one(
        cell_counting_aggregate_document.cell_counting_document
    )
    measurement_document = one(
        cell_counting_document_item.measurement_aggregate_document.measurement_document
    )
    measurement_document.measurement_identifier = ""


def test_get_model() -> None:
    parser = ViCellBluParser(TimestampParser())
    result = parser._get_model(get_data(), get_filename())
    _clear_measurement_identifier(result)
    assert result == get_model()
