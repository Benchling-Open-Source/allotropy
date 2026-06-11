from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from itertools import chain

from allotropy.calcdocs.config import (
    CalcDocsConfig,
    CalculatedDataConfig,
    CalculatedDataConfigWithOptional,
    MeasurementConfig,
)
from allotropy.calcdocs.view import ViewData
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)


@dataclass(frozen=True)
class Measurement:
    name: str
    field: str
    required: bool = False


@dataclass(frozen=True)
class CalcDoc:
    name: str
    field: str
    sources: list[str] = dataclass_field(default_factory=list)
    view: str = ""
    unit: str | None = None
    description: str | None = None
    description_field: str | None = None
    required: bool = False
    optional: bool = False
    source_only: bool = False
    output_name: str | None = None


Node = Measurement | CalcDoc


def build_calc_docs(
    nodes: list[Node],
    views: dict[str, ViewData],
) -> list[CalculatedDocument]:
    measurements: dict[str, MeasurementConfig] = {}
    calc_configs: dict[int, CalculatedDataConfig] = {}

    for node in nodes:
        if isinstance(node, Measurement):
            measurements[node.name] = MeasurementConfig(
                name=node.name,
                value=node.field,
                required=node.required,
            )

    for idx, node in enumerate(nodes):
        if isinstance(node, CalcDoc):
            _build_calc_config(idx, node, nodes, views, measurements, calc_configs)

    top_level_configs = [
        calc_configs[idx]
        for idx, node in enumerate(nodes)
        if isinstance(node, CalcDoc) and idx in calc_configs and not node.source_only
    ]

    result = CalcDocsConfig(top_level_configs).construct()
    return list(chain.from_iterable(doc.iter_struct() for doc in result))


def _build_calc_config(
    idx: int,
    node: CalcDoc,
    all_nodes: list[Node],
    views: dict[str, ViewData],
    measurements: dict[str, MeasurementConfig],
    calc_configs: dict[int, CalculatedDataConfig],
) -> CalculatedDataConfig:
    if idx in calc_configs:
        return calc_configs[idx]

    view_data = views[node.view]

    source_configs: list[CalculatedDataConfig | MeasurementConfig] = []
    for source_name in node.sources:
        if source_name in measurements:
            source_configs.append(measurements[source_name])
        else:
            source_idx, source_node = _find_node(source_name, all_nodes)
            source_config = _build_calc_config(
                source_idx, source_node, all_nodes, views, measurements, calc_configs
            )
            source_configs.append(source_config)

    config: CalculatedDataConfig
    if node.optional:
        config = CalculatedDataConfigWithOptional(
            name=node.output_name or node.name,
            value=node.field,
            view_data=view_data,
            source_configs=tuple(source_configs),
            unit=node.unit,
            description=node.description,
            description_value_key=node.description_field,
            required=node.required,
            optional=True,
        )
    else:
        config = CalculatedDataConfig(
            name=node.output_name or node.name,
            value=node.field,
            view_data=view_data,
            source_configs=tuple(source_configs),
            unit=node.unit,
            description=node.description,
            description_value_key=node.description_field,
            required=node.required,
        )
    calc_configs[idx] = config
    return config


def _find_node(name: str, nodes: list[Node]) -> tuple[int, CalcDoc]:
    for idx, node in enumerate(nodes):
        if isinstance(node, CalcDoc) and node.name == name:
            return idx, node
    msg = f"CalcDoc source '{name}' not found in nodes list"
    raise ValueError(msg)
