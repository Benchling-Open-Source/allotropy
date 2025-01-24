from __future__ import annotations

from dataclasses import dataclass

from allotropy.calcdocs.view import ViewData


@dataclass(frozen=True)
class CalculatedDataConfig:
    name: str
    value: str
    view_data: ViewData
    source_configs: list[CalculatedDataConfig | MeasurementConfig]


@dataclass(frozen=True)
class MeasurementConfig:
    name: str
    value: str
