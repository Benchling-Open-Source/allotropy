from itertools import chain

from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.config import CalculatedDataConfig, MeasurementConfig
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
)
from allotropy.parsers.utils.uuids import random_uuid_str


class AppbioQuantstudioDAConstructor:
    def get_data_source(
        self,
        config: CalculatedDataConfig | MeasurementConfig,
        keys: list[str],
        element: Element,
    ) -> DataSource:
        if isinstance(config, CalculatedDataConfig):
            element = self.apply_calc_data_config_specific(config, keys)

        if value := element.get(config.value):
            return DataSource(
                feature=config.name,
                reference=element.get("uuid"),
                value=value,
            )
        return None

    def get_calc_doc(
        self,
        config: CalculatedDataConfig,
        keys: list[str],
        element: Element,
    ) -> CalculatedDocument | None:
        if value := element.get(config.value):
            return CalculatedDocument(
                uuid=random_uuid_str(),
                name=config.name,
                value=value,
                data_sources=[
                    self.get_data_source(source_config, keys, element)
                    for source_config in config.source_configs
                ],
            )
        return None

    def apply_calc_data_config_specific(
        self,
        config: CalculatedDataConfig,
        keys: list[str],
    ) -> CalculatedDocument | None:
        element = config.view_data.get_leaf_item(*keys)[0]
        if calc_doc := self.get_calc_doc(config, keys, element):
            return calc_doc
        return None

    def apply_calc_data_config(self, config: CalculatedDataConfig) -> list[CalculatedDocument]:
        calc_docs = []
        for keys in config.view_data.iter_keys():
            for element in config.view_data.get_leaf_item(*keys):
                if calc_doc := self.get_calc_doc(config, keys, element):
                    calc_docs.append(calc_doc)
        return calc_docs

    def construct(self, configs: list[CalculatedDataConfig]) -> list[CalculatedDocument]:
        return list(chain(*[self.apply_calc_data_config(config) for config in configs]))
