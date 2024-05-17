from __future__ import annotations

from dataclasses import dataclass

from allotropy.parsers.lines_reader import LinesReader


@dataclass
class DeviceInfo:
    lines: list[str]

    @staticmethod
    def create(reader: LinesReader) -> DeviceInfo:
        lines = list(reader.pop_until_empty())
        reader.drop_empty()
        return DeviceInfo(lines)


@dataclass
class AssayInfo:
    lines: list[str]

    @staticmethod
    def create(reader: LinesReader) -> AssayInfo:
        lines = list(reader.pop_until_empty())
        reader.drop_empty()
        return AssayInfo(lines)


@dataclass
class AssayData:
    lines: list[str]

    @staticmethod
    def create(reader: LinesReader) -> AssayData:
        lines = reader.lines[reader.current_line :]
        return AssayData(lines)


@dataclass
class Data:
    device_info: DeviceInfo
    assay_info: AssayInfo
    assay_data: AssayData

    @staticmethod
    def create(reader: LinesReader) -> Data:
        return Data(
            device_info=DeviceInfo.create(reader),
            assay_info=AssayInfo.create(reader),
            assay_data=AssayData.create(reader),
        )
