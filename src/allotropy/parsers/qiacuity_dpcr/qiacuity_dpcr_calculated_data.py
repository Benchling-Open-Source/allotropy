from __future__ import annotations

from collections.abc import Iterable

from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.dpcr import (
    CalculatedDataItem,
    DataSource,
)
from allotropy.parsers.qiacuity_dpcr.constants import CALCULATED_DATA_CONFIGS
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument as UtilsCalculatedDocument,
    DataSource as UtilsDataSource,
    Referenceable as UtilsReferenceable,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def _iter_row_calculated_docs(row: SeriesData) -> Iterable[UtilsCalculatedDocument]:
    measurement_identifier = row.get(str, "_measurement_identifier")
    if not measurement_identifier:
        return []

    docs: list[UtilsCalculatedDocument] = []

    measurement_ref = UtilsReferenceable(uuid=measurement_identifier)

    for conf in CALCULATED_DATA_CONFIGS:
        value = row.get(float, conf["keys"])
        if value is None:
            continue
        docs.append(
            UtilsCalculatedDocument(
                uuid=random_uuid_str(),
                name=conf["name"],
                value=float(value),
                unit=conf["unit"],
                data_sources=[
                    UtilsDataSource(
                        feature=conf.get("feature", conf["name"]),
                        reference=measurement_ref,
                    )
                ],
            )
        )

    return docs


def _docs_to_benchling_items(
    docs: Iterable[UtilsCalculatedDocument],
) -> list[CalculatedDataItem]:
    items: list[CalculatedDataItem] = []
    for doc in docs:
        for flat_doc in doc.iter_struct():
            items.append(
                CalculatedDataItem(
                    identifier=flat_doc.uuid,
                    name=flat_doc.name,
                    value=flat_doc.value,
                    unit=flat_doc.unit or "",
                    data_sources=[
                        DataSource(
                            identifier=ds.reference.uuid,
                            feature=ds.feature,
                        )
                        for ds in flat_doc.data_sources
                    ],
                )
            )
    return items


def create_calculated_data(rows: list[SeriesData]) -> list[CalculatedDataItem]:
    docs: list[UtilsCalculatedDocument] = []
    for row in rows:
        docs.extend(list(_iter_row_calculated_docs(row)))
    return _docs_to_benchling_items(docs)
