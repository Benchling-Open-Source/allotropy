from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.values import assert_not_none

AggregateDocumentT = TypeVar("AggregateDocumentT")


def get_calculated_data_aggregate_document(
    calculated_documents: Sequence[CalculatedDocument] | None,
    *,
    aggregate_document_class: Callable[..., AggregateDocumentT],
    document_item_class: Callable[..., Any],
    data_source_aggregate_document_class: Callable[..., Any],
    data_source_document_item_class: Callable[..., Any],
    default_unit: str | None = None,
    result_field: str = "calculated_result",
    description_field: str = "calculation_description",
) -> AggregateDocumentT | None:
    """Maps calculated documents to a schema's calculated data aggregate document.

    Each schema generates its own model classes for this document, so they are passed in. The
    documents must already be flattened: data sources reference other calculated documents by
    identifier only.

    `default_unit` is used for documents without a unit; without one, such a document is an error.
    `result_field` and `description_field` name the item's result and description fields, which
    differ in schemas that do not follow the core calculated data document.
    """
    if not calculated_documents:
        return None

    return aggregate_document_class(
        calculated_data_document=[
            add_custom_information_document(
                document_item_class(
                    calculated_data_identifier=document.uuid,
                    calculated_data_name=document.name,
                    data_source_aggregate_document=(
                        data_source_aggregate_document_class(
                            data_source_document=[
                                data_source_document_item_class(
                                    data_source_identifier=data_source.reference.uuid,
                                    data_source_feature=data_source.feature,
                                )
                                for data_source in document.data_sources
                            ]
                        )
                        if document.data_sources
                        else None
                    ),
                    **{
                        result_field: TQuantityValue(
                            value=document.value,
                            unit=assert_not_none(
                                document.unit or default_unit,
                                msg=f"Expected a unit for calculated data '{document.name}'.",
                            ),
                        ),
                        description_field: document.description,
                    },
                ),
                document.custom_info,
            )
            for document in calculated_documents
        ]
    )
