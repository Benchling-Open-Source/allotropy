from __future__ import annotations

from dataclasses import dataclass
import ntpath
import re

from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.values import assert_not_none


@dataclass
class DeviceInfo:
    device_identifier: str
    model_number: str
    equipment_serial_number: str
    data_system_instance_id: str
    basename: str
    file_name: str
    unc_path: str
    software_name: str
    software_version: str
    measurement_time: str
    analyst: str

    @staticmethod
    def create(reader: LinesReader) -> DeviceInfo:
        data = {}
        for i in range(3):  # for first three lines
            line = assert_not_none(
                reader.pop(),
                msg=f"Unable to read line number {i+1}",
            )
            for element in line.split(";"):
                parts = element.split(":", maxsplit=1)
                if len(parts) > 1:
                    data[parts[0].strip()] = parts[1].strip()

        path = assert_not_none(
            reader.pop(),
            msg="Unable to read file path",
        )

        basename = ntpath.basename(path)
        file_name, *_ = basename.split(".", maxsplit=1)

        reader.drop_until_empty()
        reader.drop_empty()

        analyzer_serial_number = assert_not_none(
            data.get("Analyzer Serial number"),
            msg="Unable to find analyzer serial number.",
        )

        analyzer_serial_match = assert_not_none(
            re.match(r"^(\w+)-(\w+)", analyzer_serial_number),
            msg="Unable to parse analyzer serial number.",
        )

        computer_name = assert_not_none(
            data.get("Computer name"),
            msg="Unable to find computer name",
        )

        software_info = assert_not_none(
            data.get("Software version"),
            msg="Unable to find software version",
        )

        software_info_match = assert_not_none(
            re.match(r"^ImmunoSpot ([\d\.]+)$", software_info),
            msg="Unable to parse software version",
        )

        counted = assert_not_none(
            data.get("Counted"),
            msg="Unable to find counted timestamp.",
        )

        authenticated_user = assert_not_none(
            data.get("Authenticated user"),
            msg="Unable to find authenticated user.",
        )

        return DeviceInfo(
            device_identifier=analyzer_serial_match.group(1),
            model_number=analyzer_serial_match.group(2),
            equipment_serial_number=analyzer_serial_number,
            data_system_instance_id=computer_name,
            basename=basename,
            file_name=file_name,
            unc_path=path,
            software_name="ImmunoSpot",
            software_version=software_info_match.group(1),
            measurement_time=counted,
            analyst=authenticated_user,
        )


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
