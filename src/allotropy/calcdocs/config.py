from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from itertools import chain

from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import Keys, ViewData
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
)
from allotropy.parsers.utils.uuids import random_uuid_str


@dataclass(frozen=True)
class CalcDocsConfig:
    configs: list[CalculatedDataConfig]

    def construct(self) -> list[CalculatedDocument]:
        cache: dict[str, CalculatedDocument | None] = {}
        return list(chain(*[config.construct(cache) for config in self.configs]))


@dataclass(frozen=True)
class CalculatedDataConfig:
    name: str
    value: str
    view_data: ViewData
    source_configs: tuple[CalculatedDataConfig | MeasurementConfig, ...]
    unit: str | None = None
    description: str | None = None
    required: bool = False

    def iter_data_sources(
        self,
        parent_keys: Keys,
        _: list[Element],
        cache: dict[str, CalculatedDocument | None],
    ) -> Iterator[DataSource]:
        keys = self.view_data.filter_keys(parent_keys)
        item = self.view_data.get_item(keys)
        sub_keys_iterator = item.iter_keys() if isinstance(item, ViewData) else [Keys()]

        for sub_keys in sub_keys_iterator:
            if calc_doc := self.get_calc_doc(keys.append(sub_keys), cache):
                yield DataSource(
                    feature=calc_doc.name,
                    reference=calc_doc,
                    value=calc_doc.value,
                )

    def _get_calc_doc_inner(
        self,
        keys: Keys,
        cache: dict[str, CalculatedDocument | None],
    ) -> CalculatedDocument | None:
        elements = self.view_data.get_leaf_items(keys)
        value = elements[0].get_float_or_none(self.value)

        if value is None:
            return None

        data_sources = []
        for s_config in self.source_configs:
            if sources := list(s_config.iter_data_sources(keys, elements, cache)):
                data_sources.extend(sources)
            elif s_config.required:
                return None

        if not data_sources:
            return None

        return CalculatedDocument(
            uuid=random_uuid_str(),
            name=self.name,
            value=value,
            data_sources=data_sources,
            unit=self.unit,
            description=self.description,
        )

    def get_cache_key(self, keys: Keys) -> str:
        return f"{self.name} {self.value} {keys}"

    def get_calc_doc(
        self,
        keys: Keys,
        cache: dict[str, CalculatedDocument | None],
    ) -> CalculatedDocument | None:
        key = self.get_cache_key(keys)
        if result := cache.get(key):
            return result
        result = self._get_calc_doc_inner(keys, cache)
        cache[key] = result
        return result

    def construct(
        self, cache: dict[str, CalculatedDocument | None]
    ) -> list[CalculatedDocument]:
        return [
            calc_doc
            for keys in self.view_data.iter_keys()
            if (calc_doc := self.get_calc_doc(keys, cache))
        ]


@dataclass(frozen=True)
class MeasurementConfig:
    name: str
    value: str
    required: bool = False

    def iter_data_sources(
        self,
        _: Keys,
        elements: list[Element],
        __: dict[str, CalculatedDocument | None],
    ) -> Iterator[DataSource]:
        for element in elements:
            if (value := element.get_float_or_none(self.value)) is not None:
                yield DataSource(
                    feature=self.name,
                    reference=element,
                    value=value,
                )
