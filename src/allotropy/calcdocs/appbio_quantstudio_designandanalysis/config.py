from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from allotropy.calcdocs.config import CalculatedDataConfig
from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import Keys, ViewData
from allotropy.parsers.utils.calculated_data_documents.definition import DataSource


@dataclass(frozen=True)
class CalculatedDataConfigWithOptional(CalculatedDataConfig):
    optional: bool = False

    def iter_data_sources(
        self, parent_keys: Keys, elements: list[Element]
    ) -> Iterator[DataSource]:
        keys = self.view_data.filter_keys(parent_keys)
        item = self.view_data.get_item(keys)
        sub_keys_iterator = item.iter_keys() if isinstance(item, ViewData) else [Keys()]

        for sub_keys in sub_keys_iterator:
            new_keys = keys.append(sub_keys)
            if calc_doc := self.get_calc_doc(new_keys):
                yield DataSource(
                    feature=calc_doc.name,
                    reference=calc_doc,
                    value=None,  # should be calc_doc.value
                )
            elif self.optional:
                for sub_config in self.source_configs:
                    yield from sub_config.iter_data_sources(new_keys, elements)
