from collections.abc import Iterator

from allotropy.calcdocs.config import CalculatedDataConfig
from allotropy.calcdocs.constructor import Constructor
from allotropy.calcdocs.view import ViewData
from allotropy.parsers.utils.calculated_data_documents.definition import DataSource


class ConstructorWithOptional(Constructor):
    def iter_calc_doc_data_sources(
        self, config: CalculatedDataConfig, parent_keys: dict[str, str]
    ) -> Iterator[DataSource]:
        keys = config.view_data.filter_keys(parent_keys)
        item = config.view_data.get_item(keys)
        empty: dict[str, str] = {}
        sub_keys_iterator = item.iter_keys() if isinstance(item, ViewData) else [empty]

        for sub_keys in sub_keys_iterator:
            if calc_doc := self.get_calc_doc(config, {**keys, **sub_keys}):
                yield DataSource(
                    feature=config.name,
                    reference=calc_doc,
                    value=None,  # should be calc_doc.value
                )
            elif getattr(config, "optional", False):
                for sub_config in config.source_configs:
                    if isinstance(sub_config, CalculatedDataConfig):
                        yield from self.iter_calc_doc_data_sources(
                            sub_config, parent_keys
                        )
