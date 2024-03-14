from __future__ import annotations

from dataclasses import dataclass

from allotropy.parsers.lines_reader import CsvReader


@dataclass(frozen=True)
class DataV3:
    @staticmethod
    def create(_: CsvReader) -> DataV3:
        return DataV3()
