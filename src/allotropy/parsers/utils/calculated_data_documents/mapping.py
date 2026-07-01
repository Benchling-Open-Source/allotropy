from __future__ import annotations

from typing import Any

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)


def map_calculated_data_documents(
    calculated_data: list[CalculatedDocument] | None,
    aggregate_document_cls: type,
    document_item_cls: type,
    data_source_aggregate_cls: type,
    data_source_item_cls: type,
    *,
    unit_fallback: str | None = None,
    include_custom_info: bool = False,
) -> Any:
    if not calculated_data:
        return None

    return aggregate_document_cls(
        calculated_data_document=[
            _map_item(
                item,
                document_item_cls=document_item_cls,
                data_source_aggregate_cls=data_source_aggregate_cls,
                data_source_item_cls=data_source_item_cls,
                unit_fallback=unit_fallback,
                include_custom_info=include_custom_info,
            )
            for item in calculated_data
        ]
    )


def _map_item(
    item: CalculatedDocument,
    document_item_cls: type,
    data_source_aggregate_cls: type,
    data_source_item_cls: type,
    *,
    unit_fallback: str | None = None,
    include_custom_info: bool = False,
) -> Any:
    unit = item.unit or unit_fallback or "(unitless)"
    data_source_agg = (
        data_source_aggregate_cls(
            data_source_document=[
                data_source_item_cls(
                    data_source_identifier=source.reference.uuid,
                    data_source_feature=source.feature,
                )
                for source in item.data_sources
            ]
        )
        if item.data_sources
        else None
    )
    doc_item = document_item_cls(
        calculated_data_identifier=item.uuid,
        calculated_data_name=item.name,
        calculation_description=item.description,
        calculated_result=TQuantityValue(value=item.value, unit=unit),
        data_source_aggregate_document=data_source_agg,
    )
    if include_custom_info:
        return add_custom_information_document(doc_item, item.custom_info)
    return doc_item


def map_calculated_data_documents_for_dpcr(
    calculated_data: list[CalculatedDocument] | None,
    aggregate_document_cls: type,
    document_item_cls: type,
    data_source_aggregate_cls: type,
    data_source_item_cls: type,
) -> Any:
    if not calculated_data:
        return None

    return aggregate_document_cls(
        calculated_data_document=[
            document_item_cls(
                calculated_data_identifier=item.uuid,
                calculated_data_name=item.name,
                calculated_datum=TQuantityValue(
                    value=item.value, unit=item.unit or "(unitless)"
                ),
                data_source_aggregate_document=data_source_aggregate_cls(
                    data_source_document=[
                        data_source_item_cls(
                            data_source_identifier=source.reference.uuid,
                            data_source_feature=source.feature,
                        )
                        for source in item.data_sources
                    ]
                ),
            )
            for item in calculated_data
        ]
    )
