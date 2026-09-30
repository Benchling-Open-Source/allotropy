from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat


@dataclass
class Referenceable:
    uuid: str


@dataclass(frozen=True)
class DataSource:
    feature: str
    reference: CalculatedDocument | Referenceable
    value: JsonFloat | None = None


@dataclass
class CalculatedDocument(Referenceable):
    name: str
    value: JsonFloat
    data_sources: list[DataSource]
    unit: str | None = None
    description: str | None = None
    iterated: bool = False
    custom_info: dict[str, Any] | None = None

    def iter_struct(self) -> Iterator[CalculatedDocument]:
        if self.iterated:
            return

        self.iterated = True
        yield self
        for data_source in self.data_sources:
            if isinstance(data_source.reference, CalculatedDocument):
                yield from data_source.reference.iter_struct()
