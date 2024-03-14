from __future__ import annotations

from dataclasses import dataclass

from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.values import (
    assert_not_none,
)


@dataclass(frozen=True)
class BackgroundInfo:
    info: str

    @staticmethod
    def create(reader: CsvReader) -> BackgroundInfo:
        line = assert_not_none(
            reader.drop_until_inclusive("^Results for"),
            msg="Unable to find background information.",
        )
        return BackgroundInfo(line)


@dataclass(frozen=True)
class DataV2:
    background_info: BackgroundInfo

    @staticmethod
    def create(reader: CsvReader) -> DataV2:
        return DataV2(
            background_info=BackgroundInfo.create(reader),
        )
