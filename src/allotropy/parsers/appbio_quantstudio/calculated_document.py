from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Union

from allotropy.parsers.appbio_quantstudio.referenceable import Referenceable


@dataclass(frozen=True)
class DataSource:
    feature: str
    reference: Union[CalculatedDocument, Referenceable]


@dataclass
class CalculatedDocument(Referenceable):
    name: str
    value: float
    data_sources: list[DataSource]
    iterated: bool = False

    def iter_struct(self) -> Iterator[CalculatedDocument]:
        if self.iterated:
            return

        self.iterated = True
        yield self
        for data_source in self.data_sources:
            if isinstance(data_source.reference, CalculatedDocument):
                yield from data_source.reference.iter_struct()
