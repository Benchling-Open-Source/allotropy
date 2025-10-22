from __future__ import annotations

from collections.abc import Iterable

from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.dpcr import (
    CalculatedDataItem,
    DataSource,
)
from allotropy.parsers.qiacuity_dpcr.constants import CONFIGS
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def _iter_row_calculated_items(row: SeriesData) -> Iterable[CalculatedDataItem]:
    measurement_identifier = row.get(str, "_measurement_identifier")
    if not measurement_identifier:
        return []

    items: list[CalculatedDataItem] = []

    for conf in CONFIGS:
        value = row.get(float, conf.key)
        if value is None:
            continue
        items.append(
            CalculatedDataItem(
                identifier=random_uuid_str(),
                name=conf.name,
                value=float(value),
                unit=conf.unit,
                data_sources=[
                    DataSource(
                        identifier=measurement_identifier,
                        feature=conf.feature or conf.name,
                    )
                ],
            )
        )

    return items


def create_calculated_data(rows: list[SeriesData]) -> list[CalculatedDataItem]:
    calculated: list[CalculatedDataItem] = []
    for row in rows:
        calculated.extend(list(_iter_row_calculated_items(row)))
    return calculated
