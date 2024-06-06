from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import PureWindowsPath
import re
from typing import Optional

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.values import assert_not_none, try_float_or_none


@dataclass(frozen=True)
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

        raw_path = assert_not_none(
            reader.pop(),
            msg="Unable to read file path",
        )

        path = PureWindowsPath(raw_path)

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
            device_identifier="N/A",
            model_number=analyzer_serial_match.group(1),
            equipment_serial_number=analyzer_serial_number,
            data_system_instance_id=computer_name,
            basename=path.name,
            file_name=path.stem,
            unc_path=raw_path,
            software_name="ImmunoSpot",
            software_version=software_info_match.group(1),
            measurement_time=counted,
            analyst=authenticated_user,
        )


@dataclass(frozen=True)
class Well:
    col: str
    row: str
    value: Optional[float]

    @property
    def pos(self) -> str:
        return self.row + self.col


@dataclass(frozen=True)
class Plate:
    name: str
    wells: dict[str, Well]

    @staticmethod
    def create(reader: LinesReader) -> Plate:
        raw_name = assert_not_none(
            reader.pop(),
            msg="Unable to read name of assay data.",
        )

        name_match = assert_not_none(
            re.search("\t\t\t(.+)", raw_name),
            msg="Unable to parse name of assay data.",
        )
        name = re.sub(r"\s+", " ", name_match.group(1))

        if "ImmunoSpot Plate Code" in name:
            name = "Spot Count"

        raw_columns = assert_not_none(
            reader.pop(),
            msg=f"Unable to read data from {name}",
        )
        columns = re.sub(r"\s+", " ", raw_columns.strip())

        reader.drop_empty()

        wells = {}
        for raw_line in reader.pop_until_empty():
            line = re.sub(r"\s+", " ", raw_line)
            if match := re.match(r"^([A-Z])\s+(.+)", line):
                raw_values = match.group(2).strip()
                for column, value in zip(columns.split(), raw_values.split()):
                    well = Well(
                        col=column,
                        row=match.group(1),
                        value=try_float_or_none(value),
                    )
                    wells[well.pos] = well

        return Plate(name, wells)

    def get_well_count(self) -> int:
        return len(self.wells)

    def iter_wells(self) -> Iterator[Well]:
        yield from self.wells.values()

    def get_well(self, pos: str) -> Well:
        return assert_not_none(
            self.wells.get(pos),
            msg=f"Unable to find well '{pos}' in plate '{self.name}'",
        )


@dataclass(frozen=True)
class AssayData:
    plates: list[Plate]
    identifier: Optional[str]
    well_count: int

    @staticmethod
    def create(reader: LinesReader) -> AssayData:
        reader.drop_until_inclusive("Unprocessed Data$")

        reader.drop_empty()
        plate_code_line = reader.get() or ""
        assert_not_none(
            re.search("Plate Code =", plate_code_line),
            msg="Unable to find ImmunoSpot Plate Code line",
        )

        identifier = (
            match.group(1)
            if (match := re.search(r"Plate Code = ([\w ]+)", plate_code_line))
            else None
        )

        plates = []
        while reader.current_line_exists():
            reader.drop_empty()
            plates.append(Plate.create(reader))
            reader.drop_empty()

        if not plates:
            error = "Unable to find plate information."
            raise AllotropeConversionError(error)

        return AssayData(plates, identifier, well_count=plates[0].get_well_count())

    def iter_wells(self) -> Iterator[Well]:
        yield from self.plates[0].iter_wells()

    def iter_plates_well(self, pos: str) -> Iterator[Well]:
        for plate in self.plates:
            yield plate.get_well(pos)


@dataclass(frozen=True)
class Data:
    device_info: DeviceInfo
    assay_data: AssayData

    @staticmethod
    def create(reader: LinesReader) -> Data:
        device_info = DeviceInfo.create(reader)

        reader.drop_empty()
        reader.drop_until_empty()  # ignore assay info
        reader.drop_empty()

        assay_data = AssayData.create(reader)
        return Data(device_info, assay_data)

    def get_plate_identifier(self) -> str:
        return (
            self.device_info.file_name
            if self.assay_data.identifier is None
            else self.assay_data.identifier
        )
