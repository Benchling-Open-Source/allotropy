from collections.abc import Iterator
from itertools import chain

from allotropy.calcdocs.config import CalculatedDataConfig, MeasurementConfig
from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import ViewData
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)
from allotropy.parsers.utils.uuids import random_uuid_str


class Constructor:
    def iter_measurement_data_sources(
        self, config: MeasurementConfig, elements: list[Element]
    ) -> Iterator[DataSource]:
        for element in elements:
            if element.get_or_none(config.value) is not None:
                yield DataSource(
                    feature=config.name,
                    reference=Referenceable(
                        element.get_str("uuid")
                    ),  # sould be just element
                    value=None,  # should be value
                )

    def iter_calc_doc_data_sources(
        self, config: CalculatedDataConfig, keys: dict[str, str]
    ) -> Iterator[DataSource]:
        item = config.view_data.get_item(keys)
        for sub_keys in item.iter_keys() if isinstance(item, ViewData) else [{}]:
            if calc_doc := self.get_calc_doc(config, {**keys, **sub_keys}):  # type: ignore[dict-item]
                yield DataSource(
                    feature=config.name,
                    reference=calc_doc,
                    value=None,  # should be calc_doc.value
                )

    def get_calc_doc(
        self,
        config: CalculatedDataConfig,
        keys: dict[str, str],
    ) -> CalculatedDocument | None:
        elements = config.view_data.get_leaf_items(keys)
        value = elements[0].get_float_or_none(config.value)

        if value is None:
            return None

        return CalculatedDocument(
            uuid=random_uuid_str(),
            name=config.name,
            value=value,
            data_sources=[
                data_source
                for source_config in config.source_configs
                for data_source in (
                    self.iter_calc_doc_data_sources(
                        source_config,
                        source_config.view_data.filter_keys(keys),
                    )
                    if isinstance(source_config, CalculatedDataConfig)
                    else self.iter_measurement_data_sources(source_config, elements)
                )
            ],
        )

    def apply_calc_data_config(
        self, config: CalculatedDataConfig
    ) -> list[CalculatedDocument]:
        return [
            calc_doc
            for keys in config.view_data.iter_keys()
            if (calc_doc := self.get_calc_doc(config, keys))
        ]

    def construct(
        self, configs: list[CalculatedDataConfig]
    ) -> list[CalculatedDocument]:
        return list(chain(*[self.apply_calc_data_config(config) for config in configs]))
