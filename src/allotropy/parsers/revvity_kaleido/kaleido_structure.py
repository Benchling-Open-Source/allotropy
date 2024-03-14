from __future__ import annotations

from dataclasses import dataclass

from allotropy.parsers.lines_reader import CsvReader


@dataclass(frozen=True)
class Data:
    @staticmethod
    def create(_: CsvReader) -> Data:
        return Data()
