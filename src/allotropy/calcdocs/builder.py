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
    sources: list[Measurement | CalcDoc] = dataclass_field(default_factory=list)
    view: str = ""
    unit: str | None = None
    description: str | None = None
    description_field: str | None = None
    required: bool = False
    optional: bool = False
    source_only: bool = False


Node = Measurement | CalcDoc


def build_calc_docs(
    nodes: list[Node],
    views: dict[str, ViewData],
) -> list[CalculatedDocument]:
    _validate_graph(nodes, views)

    measurements: dict[int, MeasurementConfig] = {}
    calc_configs: dict[int, CalculatedDataConfig] = {}

    for node in nodes:
        if isinstance(node, Measurement):
            measurements[id(node)] = MeasurementConfig(
                name=node.name,
                value=node.field,
                required=node.required,
            )

    for node in nodes:
        if isinstance(node, CalcDoc):
            _build_calc_config(node, views, measurements, calc_configs)

    top_level_configs = [
        calc_configs[id(node)]
        for node in nodes
        if isinstance(node, CalcDoc)
        and id(node) in calc_configs
        and not node.source_only
    ]

    result = CalcDocsConfig(top_level_configs).construct()
    return list(chain.from_iterable(doc.iter_struct() for doc in result))


def _validate_graph(nodes: list[Node], views: dict[str, ViewData]) -> None:
    node_set = {id(n) for n in nodes}

    for node in nodes:
        if not isinstance(node, CalcDoc):
            continue
        if node.view and node.view not in views:
            msg = (
                f"CalcDoc '{node.name}' references view '{node.view}' "
                f"but available views are: {sorted(views.keys())}"
            )
            raise ValueError(msg)
        for source in node.sources:
            if id(source) not in node_set:
                msg = (
                    f"CalcDoc '{node.name}' references source '{source.name}' "
                    f"which is not in the nodes list"
                )
                raise ValueError(msg)


def _build_calc_config(
    node: CalcDoc,
    views: dict[str, ViewData],
    measurements: dict[int, MeasurementConfig],
    calc_configs: dict[int, CalculatedDataConfig],
) -> CalculatedDataConfig:
    if id(node) in calc_configs:
        return calc_configs[id(node)]

    view_data = views[node.view]

    source_configs: list[CalculatedDataConfig | MeasurementConfig] = []
    for source in node.sources:
        if isinstance(source, Measurement):
            source_configs.append(measurements[id(source)])
        else:
            source_config = _build_calc_config(
                source, views, measurements, calc_configs
            )
            source_configs.append(source_config)

    config: CalculatedDataConfig
    if node.optional:
        config = CalculatedDataConfigWithOptional(
            name=node.name,
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
            name=node.name,
            value=node.field,
            view_data=view_data,
            source_configs=tuple(source_configs),
            unit=node.unit,
            description=node.description,
            description_value_key=node.description_field,
            required=node.required,
        )
    calc_configs[id(node)] = config
    return config


def describe_graph(nodes: list[Node]) -> str:
    lines = []
    for node in nodes:
        if isinstance(node, Measurement):
            lines.append(f"  [M] {node.name} <- element.{node.field}")
        elif isinstance(node, CalcDoc):
            prefix = "(source_only) " if node.source_only else ""
            source_names = [s.name for s in node.sources]
            lines.append(
                f"  [C] {prefix}{node.name} <- element.{node.field} "
                f"| view={node.view} | sources={source_names}"
            )
    return "\n".join(lines)
