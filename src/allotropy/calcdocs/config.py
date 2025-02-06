from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from itertools import chain

from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import Keys, ViewData
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
)
from allotropy.parsers.utils.uuids import random_uuid_str


@dataclass
class CalcDocsConfig:
    configs: tuple[CalculatedDataConfig, ...] = field(default_factory=tuple)
    cache: dict[str, CalculatedDocument | None] = field(
        init=False, default_factory=dict
    )

    @classmethod
    def create_with_cache(
        cls, config_list: tuple[CalculatedDataConfig, ...]
    ) -> CalcDocsConfig:
        configs = CalcDocsConfig()
        configs.configs = tuple(config.add_cache(configs) for config in config_list)
        return configs

    def construct(self) -> list[CalculatedDocument]:
        return list(chain(*[config.construct() for config in self.configs]))


@dataclass(frozen=True)
class CalculatedDataConfig:
    name: str
    value: str
    view_data: ViewData
    source_configs: tuple[CalculatedDataConfig | MeasurementConfig, ...]

    def add_cache(self, calc_docs_config: CalcDocsConfig) -> CalculatedDataConfig:
        return CalculatedDataConfigWithCache(
            name=self.name,
            value=self.value,
            view_data=self.view_data,
            source_configs=tuple(
                (
                    source_config.add_cache(calc_docs_config)
                    if isinstance(source_config, CalculatedDataConfig)
                    else source_config
                )
                for source_config in self.source_configs
            ),
            calc_docs_config=calc_docs_config,
        )

    def iter_data_sources(
        self, parent_keys: Keys, _: list[Element]
    ) -> Iterator[DataSource]:
        keys = self.view_data.filter_keys(parent_keys)
        item = self.view_data.get_item(keys)
        sub_keys_iterator = item.iter_keys() if isinstance(item, ViewData) else [Keys()]

        for sub_keys in sub_keys_iterator:
            if calc_doc := self.get_calc_doc(keys.append(sub_keys)):
                yield DataSource(
                    feature=calc_doc.name,
                    reference=calc_doc,
                    value=calc_doc.value,
                )

    def get_calc_doc(
        self,
        keys: Keys,
    ) -> CalculatedDocument | None:
        elements = self.view_data.get_leaf_items(keys)
        value = elements[0].get_float_or_none(self.value)

        if value is None:
            return None

        data_sources = [
            data_source
            for source_config in self.source_configs
            for data_source in source_config.iter_data_sources(keys, elements)
        ]

        if not data_sources:
            return None

        return CalculatedDocument(
            uuid=random_uuid_str(),
            name=self.name,
            value=value,
            data_sources=data_sources,
        )

    def construct(self) -> list[CalculatedDocument]:
        return [
            calc_doc
            for keys in self.view_data.iter_keys()
            if (calc_doc := self.get_calc_doc(keys))
        ]


@dataclass(frozen=True)
class CalculatedDataConfigWithCache(CalculatedDataConfig):
    calc_docs_config: CalcDocsConfig

    def get_calc_doc(
        self,
        keys: Keys,
    ) -> CalculatedDocument | None:
        key = f"{self.name} {self.value} {keys}"
        if result := self.calc_docs_config.cache.get(key):
            return result
        result = super().get_calc_doc(keys)
        self.calc_docs_config.cache[key] = result
        return result


@dataclass(frozen=True)
class MeasurementConfig:
    name: str
    value: str

    def iter_data_sources(
        self, _: Keys, elements: list[Element]
    ) -> Iterator[DataSource]:
        for element in elements:
            if (value := element.get_float_or_none(self.value)) is not None:
                yield DataSource(
                    feature=self.name,
                    reference=element,
                    value=value,
                )
