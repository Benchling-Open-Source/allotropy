from __future__ import annotations

from collections.abc import Iterable

from allotropy.parsers.qiacuity_dpcr.constants import CALCULATED_DATA_CONFIGS
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def _iter_row_calculated_docs(row: SeriesData) -> Iterable[CalculatedDocument]:
    measurement_identifier = row.get(str, "_measurement_identifier")
    if not measurement_identifier:
        return []

    docs: list[CalculatedDocument] = []

    measurement_ref = Referenceable(uuid=measurement_identifier)

    for conf in CALCULATED_DATA_CONFIGS:
        value = row.get(float, conf["keys"])
        if value is None:
            continue
        docs.append(
            CalculatedDocument(
                uuid=random_uuid_str(),
                name=conf["name"],
                value=float(value),
                unit=conf["unit"],
                data_sources=[
                    DataSource(
                        feature=conf.get("feature", conf["name"]),
                        reference=measurement_ref,
                    )
                ],
            )
        )

    return docs


def create_calculated_data(rows: list[SeriesData]) -> list[CalculatedDocument]:
    docs: list[CalculatedDocument] = []
    for row in rows:
        docs.extend(list(_iter_row_calculated_docs(row)))
    return docs
