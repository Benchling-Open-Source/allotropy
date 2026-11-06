import pytest

from allotropy.allotrope.models.adm.core.rec._2024._09.hierarchy import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
)
from allotropy.allotrope.models.adm.pcr.benchling._2023._09.dpcr import (
    CalculatedDataDocumentItem as DpcrCalculatedDataDocumentItem,
    DataSourceAggregateDocument as DpcrDataSourceAggregateDocument,
    DataSourceDocumentItem as DpcrDataSourceDocumentItem,
    TCalculatedDataAggregateDocument as DpcrCalculatedDataAggregateDocument,
)
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue
from allotropy.allotrope.schema_mappers.calculated_data import (
    get_calculated_data_aggregate_document,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)


def _map_to_core_schema(
    documents: list[CalculatedDocument] | None, default_unit: str | None = None
) -> CalculatedDataAggregateDocument | None:
    return get_calculated_data_aggregate_document(
        documents,
        aggregate_document_class=CalculatedDataAggregateDocument,
        document_item_class=CalculatedDataDocumentItem,
        data_source_aggregate_document_class=DataSourceAggregateDocument,
        data_source_document_item_class=DataSourceDocumentItem,
        default_unit=default_unit,
    )


def _document(
    unit: str | None = "%", data_sources: list[DataSource] | None = None
) -> CalculatedDocument:
    return CalculatedDocument(
        uuid="calc-1",
        name="viability",
        value=95.0,
        unit=unit,
        description="live cells over total cells",
        data_sources=(
            [DataSource(feature="cell count", reference=Referenceable(uuid="meas-1"))]
            if data_sources is None
            else data_sources
        ),
    )


@pytest.mark.parametrize("documents", [None, []])
def test_no_documents_maps_to_none(documents: list[CalculatedDocument] | None) -> None:
    assert _map_to_core_schema(documents) is None


def test_maps_document_and_data_sources() -> None:
    assert _map_to_core_schema([_document()]) == CalculatedDataAggregateDocument(
        calculated_data_document=[
            CalculatedDataDocumentItem(
                calculated_data_identifier="calc-1",
                calculated_data_name="viability",
                calculation_description="live cells over total cells",
                calculated_result=TQuantityValue(value=95.0, unit="%"),
                data_source_aggregate_document=DataSourceAggregateDocument(
                    data_source_document=[
                        DataSourceDocumentItem(
                            data_source_identifier="meas-1",
                            data_source_feature="cell count",
                        )
                    ]
                ),
            )
        ]
    )


def test_document_without_data_sources_has_no_data_source_aggregate_document() -> None:
    result = _map_to_core_schema([_document(data_sources=[])])
    assert result is not None
    assert result.calculated_data_document[0].data_source_aggregate_document is None


def test_document_without_unit_uses_default_unit() -> None:
    result = _map_to_core_schema([_document(unit=None)], default_unit="(unitless)")
    assert result is not None
    assert result.calculated_data_document[0].calculated_result == TQuantityValue(
        value=95.0, unit="(unitless)"
    )


def test_document_without_unit_or_default_unit_is_an_error() -> None:
    with pytest.raises(AllotropeConversionError, match="viability"):
        _map_to_core_schema([_document(unit=None)])


def test_custom_info_is_attached_to_the_document_item() -> None:
    document = _document()
    document.custom_info = {"method": "trypan blue"}
    result = _map_to_core_schema([document])
    assert result is not None
    custom_info = result.calculated_data_document[0].custom_information_document  # type: ignore[attr-defined]
    assert custom_info.method == "trypan blue"


def test_maps_to_schema_with_differently_named_fields() -> None:
    result = get_calculated_data_aggregate_document(
        [_document()],
        aggregate_document_class=DpcrCalculatedDataAggregateDocument,
        document_item_class=DpcrCalculatedDataDocumentItem,
        data_source_aggregate_document_class=DpcrDataSourceAggregateDocument,
        data_source_document_item_class=DpcrDataSourceDocumentItem,
        result_field="calculated_datum",
        description_field="calculated_data_description",
    )
    assert result is not None
    assert result.calculated_data_document is not None
    item = result.calculated_data_document[0]
    assert item.calculated_datum == TQuantityValue(value=95.0, unit="%")
    assert item.calculated_data_description == "live cells over total cells"
