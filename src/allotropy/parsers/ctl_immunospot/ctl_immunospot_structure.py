from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
import re

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    ImageFeature,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedData,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.lines_reader import LinesReader
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
            error = "Unable to find plate information."
            raise AllotropeConversionError(error)

        return AssayData(plates, identifier)


def _create_measurement_groups(
    assay_data: AssayData, metadata: Metadata
) -> list[MeasurementGroup]:
    well_plate_identifier = (
        assay_data.identifier or Path(assert_not_none(metadata.file_name)).stem
    )
    plate_well_count = len(assay_data.plates[0].wells)
    return [
        MeasurementGroup(
            plate_well_count=plate_well_count,
            measurements=[
                Measurement(
                    type_=MeasurementType.OPTICAL_IMAGING,
                    identifier=random_uuid_str(),
                    well_plate_identifier=well_plate_identifier,
                    location_identifier=well_position,
                    sample_identifier=f"{well_plate_identifier}_{well_position}",
                    processed_data=ProcessedData(
                        random_uuid_str(),
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


def _create_metadata(reader: LinesReader) -> Metadata:
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
    software_info = assert_not_none(
        data.get("Software version"),
        msg="Unable to find software version",
    )
    return Metadata(
        device_identifier=NOT_APPLICABLE,
        device_type="imager",
        detection_type="optical-imaging",
        model_number=assert_not_none(
            re.match(r"^(\w+)-(\w+)", analyzer_serial_number),
            msg="Unable to parse analyzer serial number.",
        ).group(1),
        equipment_serial_number=analyzer_serial_number,
        data_system_instance_id=assert_not_none(
            data.get("Computer name"),
            msg="Unable to find computer name",
        ),
        file_name=path.name,
        unc_path=raw_path,
        product_manufacturer="CTL",
        software_name="ImmunoSpot",
        software_version=assert_not_none(
            re.match(r"^ImmunoSpot ([\d\.]+)$", software_info),
            msg="Unable to parse software version",
        ).group(1),
        measurement_time=assert_not_none(
            data.get("Counted"),
            msg="Unable to find counted timestamp.",
        ),
        analyst=assert_not_none(
            data.get("Authenticated user"),
            msg="Unable to find authenticated user.",
        ),
    )


def create_data(reader: LinesReader) -> Data:
    metadata = _create_metadata(reader)

    reader.drop_empty()
    reader.drop_until_empty()  # ignore assay info
    reader.drop_empty()

    assay_data = AssayData.create(reader)
    return Data(
        metadata=metadata,
        measurement_groups=_create_measurement_groups(assay_data, metadata),
    )
