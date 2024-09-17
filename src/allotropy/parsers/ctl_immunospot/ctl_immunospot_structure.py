from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import PureWindowsPath
import re

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    ImageFeature,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedData,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.ctl_immunospot import constants
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.pandas import df_to_series_data, read_csv
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_or_nan,
)


@dataclass(frozen=True)
class Plate:
    name: str
    wells: dict[str, JsonFloat]

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
                for column, value in zip(
                    columns.split(), raw_values.split(), strict=True
                ):
                    wells[match.group(1) + column] = try_float_or_nan(value)

        return Plate(name, wells)


@dataclass(frozen=True)
class AssayData:
    plates: list[Plate]
    identifier: str | None

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
            msg = "Unable to find plate information."
            raise AllotropeConversionError(msg)

        return AssayData(plates, identifier)


def create_measurement_groups(
    assay_data: AssayData, header: Header
) -> list[MeasurementGroup]:
    well_plate_identifier = (
        assay_data.identifier or PureWindowsPath(header.file_path).stem
    )
    plate_well_count = len(assay_data.plates[0].wells)
    return [
        MeasurementGroup(
            plate_well_count=plate_well_count,
            measurement_time=header.counted_time,
            analyst=header.authenticated_user,
            measurements=[
                Measurement(
                    type_=MeasurementType.OPTICAL_IMAGING,
                    device_type=constants.DEVICE_TYPE,
                    identifier=random_uuid_str(),
                    well_plate_identifier=well_plate_identifier,
                    location_identifier=well_position,
                    sample_identifier=f"{well_plate_identifier}_{well_position}",
                    detection_type=constants.DETECTION_TYPE,
                    processed_data=ProcessedData(
                        identifier=random_uuid_str(),
                        features=[
                            ImageFeature(
                                identifier=random_uuid_str(),
                                feature=plate.name,
                                result=plate.wells[well_position],
                            )
                            for plate in assay_data.plates
                        ],
                    ),
                )
            ],
        )
        for well_position in assay_data.plates[0].wells
    ]


@dataclass
class Header:
    counted_time: str
    file_path: str
    analyzer_serial_number: str
    software_version: str
    computer_name: str
    authenticated_user: str

    @staticmethod
    def create(reader: LinesReader) -> Header:
        lines = [
            # Add missing key for file path line.
            f"File path: {line}" if line.endswith(".txt") else line
            for raw_line in reader.pop_until_empty()
            # Split rows over ';'
            for line in raw_line.split(";")
        ]
        reader.drop_empty()
        lines.extend(list(reader.pop_until_empty()))

        df = read_csv(
            StringIO("\n".join(lines)),
            sep=r"^([^:]+):\s+",
            header=None,
            engine="python",
            index_col=1,
        ).T
        data = df_to_series_data(df, index=1)

        return Header(
            counted_time=data[str, "Counted"],
            file_path=data[str, "File path"],
            analyzer_serial_number=data[str, "Analyzer Serial number"],
            software_version=data[str, "Software version"],
            computer_name=data[str, "Computer name"],
            authenticated_user=data[str, "Authenticated user"],
        )


def create_metadata(header: Header) -> Metadata:
    return Metadata(
        file_name=PureWindowsPath(header.file_path).name,
        unc_path=header.file_path,
        device_identifier=NOT_APPLICABLE,
        model_number=assert_not_none(
            re.match(r"^(\w+)-(\w+)", header.analyzer_serial_number),
            msg="Unable to parse analyzer serial number.",
        ).group(1),
        data_system_instance_id=header.computer_name,
        equipment_serial_number=header.analyzer_serial_number,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        software_name=constants.SOFTWARE_NAME,
        software_version=assert_not_none(
            re.match(r"^ImmunoSpot ([\d\.]+)$", header.software_version),
            msg="Unable to parse software version",
        ).group(1),
    )
