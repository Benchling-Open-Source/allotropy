"""High-level calcdocs API — minimal concepts, maximum discoverability.

This module provides a simplified interface for defining calculated data documents.
It requires understanding only 3 concepts:

1. Meas — a raw measurement value from your data
2. Calc — a calculated value derived from measurements or other calcs
3. GroupBy — how to partition data for each calculation

Usage:
    from allotropy.calcdocs.api import calc_docs, Calc, GroupBy, Meas

    def to_element(item: MyDataClass) -> dict:
        return {
            "uuid": item.uuid,
            "sample_id": item.sample_identifier,
            "value": item.measured_value,
            "mean": item.computed_mean,
        }

    BY_SAMPLE = GroupBy("sample_id")
    BY_SAMPLE_UUID = GroupBy("sample_id", "uuid")

    measurement = Meas("value", field="value")
    mean = Calc("mean", field="mean", sources=[measurement], group=BY_SAMPLE)

    result = calc_docs(items, to_element, nodes=[measurement, mean])
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field as dataclass_field
from itertools import chain
from typing import Any, TypeVar

from allotropy.calcdocs.appbio_quantstudio_designandanalysis.config import (
    CalculatedDataConfigWithOptional,
)
from allotropy.calcdocs.config import (
    CalcDocsConfig,
    CalculatedDataConfig,
    MeasurementConfig,
)
from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import Keys, View, ViewData
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)

T = TypeVar("T")


@dataclass(frozen=True)
class GroupBy:
    """Defines how elements are partitioned for a calculation.

    Each string in `fields` is a key in the element dict. Elements sharing the same
    values for all fields are grouped together. "uuid" is special — it groups by
    element identity (one element per group).

    Args:
        *fields: Field names to group by, outermost first.
        filter_by: Only include elements where these field values match exactly.
        exclude: Exclude elements where the field value is in the given list.
        reference: Redirect key lookups to a fixed value (for reference sample/target).
    """

    fields: tuple[str, ...] = ()
    filter_by: dict[str, str] = dataclass_field(default_factory=dict)
    exclude: dict[str, list[str]] = dataclass_field(default_factory=dict)
    reference: dict[str, str] = dataclass_field(default_factory=dict)

    def __init__(
        self,
        *fields: str,
        filter_by: dict[str, str] | None = None,
        exclude: dict[str, list[str]] | None = None,
        reference: dict[str, str] | None = None,
    ):
        object.__setattr__(self, "fields", fields)
        object.__setattr__(self, "filter_by", filter_by or {})
        object.__setattr__(self, "exclude", exclude or {})
        object.__setattr__(self, "reference", reference or {})


@dataclass(frozen=True)
class Meas:
    """A raw measurement value from element data.

    Args:
        name: Feature name for this measurement in the output document.
        field: Key in the element dict containing the value.
        required: If True, a missing measurement causes the parent calc to be skipped.
    """

    name: str
    field: str
    required: bool = False


@dataclass(frozen=True)
class Calc:
    """A calculated value derived from measurements or other calculations.

    Args:
        name: Name of the output calculated document.
        field: Key in the element dict containing the pre-computed value.
        sources: Direct references to Meas or Calc nodes this depends on.
        group: How to partition elements for this calculation.
        unit: Unit string for the output value.
        description: Static description for the output document.
        description_field: Key in element dict for a dynamic description value.
        required: If True, a missing value causes the parent calc to be skipped.
        optional: If True, when this calc can't resolve, fall through to its sources.
        source_only: If True, this node is only a dependency — not emitted top-level.
    """

    name: str
    field: str
    sources: list[Meas | Calc] = dataclass_field(default_factory=list)
    group: GroupBy = dataclass_field(default_factory=GroupBy)
    unit: str | None = None
    description: str | None = None
    description_field: str | None = None
    required: bool = False
    optional: bool = False
    source_only: bool = False


CalcNode = Meas | Calc


def calc_docs(
    items: list[T],
    to_element: Callable[[T], dict[str, Any]],
    nodes: list[CalcNode],
) -> list[CalculatedDocument]:
    """Build calculated data documents from domain objects.

    This is the single entry point. It:
    1. Converts your domain objects to elements using to_element
    2. Automatically builds view hierarchies from GroupBy specs
    3. Resolves the dependency graph and produces CalculatedDocuments

    Args:
        items: Your domain objects (WellItem, Measurement, etc.)
        to_element: Function that converts one item to a flat dict.
                    Must include a "uuid" key for element identity.
        nodes: List of Meas and Calc nodes defining the dependency graph.

    Returns:
        Flattened list of CalculatedDocuments ready for the schema mapper.
    """
    elements = _build_elements(items, to_element)
    views = _build_views(nodes, elements)

    _validate(nodes)

    measurements: dict[int, MeasurementConfig] = {}
    calc_configs: dict[int, CalculatedDataConfig] = {}

    for node in nodes:
        if isinstance(node, Meas):
            measurements[id(node)] = MeasurementConfig(
                name=node.name,
                value=node.field,
                required=node.required,
            )

    for node in nodes:
        if isinstance(node, Calc):
            _resolve(node, views, measurements, calc_configs)

    top_level_configs = [
        calc_configs[id(node)]
        for node in nodes
        if isinstance(node, Calc) and id(node) in calc_configs and not node.source_only
    ]

    result = CalcDocsConfig(top_level_configs).construct()
    return list(chain.from_iterable(doc.iter_struct() for doc in result))


def _build_elements(
    items: list[T], to_element: Callable[[T], dict[str, Any]]
) -> list[Element]:
    elements = []
    for item in items:
        data = to_element(item)
        uuid = data.pop("uuid", None)
        if uuid is None:
            msg = "to_element must return a dict with a 'uuid' key"
            raise ValueError(msg)
        elements.append(Element(uuid=str(uuid), data=data))
    return elements


def _build_views(nodes: list[CalcNode], elements: list[Element]) -> dict[int, ViewData]:
    views: dict[int, ViewData] = {}
    for node in nodes:
        if isinstance(node, Calc):
            view = _group_by_to_view(node.group)
            views[id(node)] = view.apply(elements)
    return views


def _group_by_to_view(group: GroupBy) -> View:
    """Convert a GroupBy spec into a View hierarchy."""
    fields = list(group.fields)
    if not fields:
        msg = "GroupBy must specify at least one field"
        raise ValueError(msg)

    # Build view chain from innermost to outermost
    view: View | None = None
    for field_name in reversed(fields):
        view = _GroupByFieldView(
            field=field_name,
            sub_view=view,
            filter_spec=group.filter_by,
            exclude_spec=group.exclude,
            reference_spec=group.reference,
        )
    if view is None:
        msg = "GroupBy must specify at least one field"
        raise ValueError(msg)
    return view


class _GroupByFieldView(View):
    """Internal view that implements GroupBy semantics."""

    def __init__(
        self,
        field: str,
        sub_view: View | None = None,
        filter_spec: dict[str, str] | None = None,
        exclude_spec: dict[str, list[str]] | None = None,
        reference_spec: dict[str, str] | None = None,
    ):
        super().__init__(name=field, sub_view=sub_view)
        self.field = field
        self.filter_spec = filter_spec or {}
        self.exclude_spec = exclude_spec or {}
        self.reference_spec = reference_spec or {}

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items: dict[str, list[Element]] = defaultdict(list)
        for element in elements:
            if not self._passes_filters(element):
                continue
            if self.field == "uuid":
                key: str | None = element.uuid
            else:
                key = element.get_str_or_none(self.field)
            if key is not None and not self._is_excluded(key):
                items[key].append(element)
        return dict(items)

    def _passes_filters(self, element: Element) -> bool:
        for field_name, required_value in self.filter_spec.items():
            actual = element.get_str_or_none(field_name)
            if actual != required_value:
                return False
        return True

    def _is_excluded(self, key: str) -> bool:
        if self.field in self.exclude_spec:
            return key in self.exclude_spec[self.field]
        return False

    def filter_keys(self, keys: Keys) -> Keys:
        filtered_keys = self.sub_view.filter_keys(keys) if self.sub_view else Keys()
        if self.field in self.reference_spec:
            ref_value = self.reference_spec[self.field]
            if keys.get_or_none(self.name):
                return filtered_keys.overwrite(self.name, ref_value)
            return filtered_keys
        if key := keys.get_or_none(self.name):
            return filtered_keys.overwrite(self.name, key.value)
        return filtered_keys


def _validate(nodes: list[CalcNode]) -> None:
    node_set = {id(n) for n in nodes}
    for node in nodes:
        if not isinstance(node, Calc):
            continue
        for source in node.sources:
            if id(source) not in node_set:
                msg = (
                    f"Calc '{node.name}' references source '{source.name}' "
                    f"which is not in the nodes list"
                )
                raise ValueError(msg)


def _resolve(
    node: Calc,
    views: dict[int, ViewData],
    measurements: dict[int, MeasurementConfig],
    calc_configs: dict[int, CalculatedDataConfig],
) -> CalculatedDataConfig:
    if id(node) in calc_configs:
        return calc_configs[id(node)]

    view_data = views[id(node)]

    source_configs: list[CalculatedDataConfig | MeasurementConfig] = []
    for source in node.sources:
        if isinstance(source, Meas):
            source_configs.append(measurements[id(source)])
        else:
            source_config = _resolve(source, views, measurements, calc_configs)
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
