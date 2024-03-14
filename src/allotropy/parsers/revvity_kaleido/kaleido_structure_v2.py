from __future__ import annotations

from dataclasses import dataclass

from allotropy.parsers.lines_reader import CsvReader


@dataclass(frozen=True)
class DataV2:
    @staticmethod
    def create(_: CsvReader) -> DataV2:
        return DataV2()
