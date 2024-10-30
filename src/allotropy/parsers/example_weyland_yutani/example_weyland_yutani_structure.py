from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.example_weyland_yutani import constants
from allotropy.parsers.utils.uuids import random_uuid_str


@dataclass(frozen=True)
class BasicAssayInfo:
    protocol_id: str
    assay_id: str
    checksum: str | None

    @staticmethod
    def create(bottom: pd.DataFrame | None) -> BasicAssayInfo:
        checksum = (
            None
            if (bottom is None) or (bottom.iloc[0, 0] != "Checksum")
            else str(bottom.iloc[0, 1])
        )
        return BasicAssayInfo(
            # NOTE: in real code these values would be read from data
            protocol_id=constants.PROTOCOL_ID,
            assay_id=constants.ASSAY_ID,
            checksum=checksum,
        )


@dataclass(frozen=True)
class Instrument:
    serial_number: str
    nickname: str

    # TODO(tutorial): extract and fill in real values for serial number and nickname
    @staticmethod
    def create() -> Instrument:
        return Instrument(serial_number="", nickname="")


@dataclass(frozen=True)
class Result:
    col: str
    row: str
    value: float


@dataclass(frozen=True)
class Plate:
    number: str
    results: list[Result]

    @property
    def number_of_wells(self) -> int:
        return len(self.results)

    @staticmethod
    def create(df: pd.DataFrame | None) -> list[Plate]:
        if df is None:
            return []
        pivoted = df.T
        if pivoted.iloc[1, 0] != "A":
            msg = "Column header(s) not found."
            raise AllotropeConversionError(msg)
        stripped = pivoted.drop(0, axis="index").drop(0, axis="columns")
        rows, cols = stripped.shape
        stripped.index = [df.iloc[0, i + 1] for i in range(rows)]  # type: ignore
        stripped.columns = [str(int(df.iloc[i, 0])) for i in range(1, cols + 1)]  # type: ignore
        return [
            Plate(
                number="0",
                results=[
                    Result(col, row, float(stripped.loc[col, row]))
                    for col, row in stripped.stack().index
                ],
            )
        ]


def create_metadata(instrument: Instrument, file_path: str) -> Metadata:
    return Metadata(
        file_name=Path(file_path).name,
        unc_path=file_path,
        model_number=instrument.serial_number,
        device_identifier=instrument.nickname,
    )


def create_measurement_group(
    plate: Plate, basic_assay_info: BasicAssayInfo
) -> MeasurementGroup:
    return MeasurementGroup(
        plate_well_count=plate.number_of_wells,
        analytical_method_identifier=basic_assay_info.protocol_id,
        experimental_data_identifier=basic_assay_info.assay_id,
        # TODO(tutorial): extract and return actual measurement time
        measurement_time="2022-12-31",
        measurements=[
            Measurement(
                type_=MeasurementType.FLUORESCENCE,
                device_type=constants.DEVICE_TYPE,
                identifier=random_uuid_str(),
                detection_type=constants.DETECTION_TYPE,
                sample_identifier=f"Plate {plate.number}",
                location_identifier=f"{result.col}{result.row}",
                fluorescence=result.value,
            )
            for result in plate.results
        ],
    )
