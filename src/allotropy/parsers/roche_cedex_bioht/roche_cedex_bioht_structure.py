from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from dateutil import parser
import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat, NaN
from allotropy.allotrope.schema_mappers.adm.solution_analyzer.rec._2024._09.solution_analyzer import (
    Analyte,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.exceptions import AllotropyParserError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.roche_cedex_bioht.constants import (
    BELOW_TEST_RANGE,
    MAX_MEASUREMENT_TIME_GROUP_DIFFERENCE,
    OPTICAL_DENSITY,
    SOLUTION_ANALYZER,
)
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


@dataclass(frozen=True)
class Title:
    data_processing_time: str
    analyst: str
    device_serial_number: str
    model_number: str | None = None
    software_version: str | None = None

    @staticmethod
    def create(title_data: SeriesData) -> Title:
        return Title(
            title_data[str, "data processing time"],
            title_data[str, "analyst"],
            title_data[str, "device serial number"],
            title_data.get(str, "model number"),
            title_data.get(str, "software version"),
        )


@dataclass(frozen=True)
class RawMeasurement:
    name: str
    measurement_time: str
    concentration_value: JsonFloat
    unit: str
    error: str | None = None

    @staticmethod
    def create(data: SeriesData) -> RawMeasurement:
        error = data.get(str, "flag", "").strip()
        # TODO: handle other errors
        if BELOW_TEST_RANGE not in error:
            error = ""
        concentration_value = (
            NaN
            if BELOW_TEST_RANGE in error
            else data.get(float, "concentration value", NaN)
        )
        return RawMeasurement(
            data[str, "analyte name"],
            data[str, "measurement time"],
            concentration_value,
            data[str, "concentration unit"],
            error or None,
        )


def create_measurements(data: pd.DataFrame) -> dict[str, dict[str, RawMeasurement]]:
    measurements = sorted(
        map_rows(data, RawMeasurement.create), key=lambda a: a.measurement_time
    )

    # Dict from measurement time to data
    groups: defaultdict[str, dict[str, RawMeasurement]] = defaultdict(dict)

    current_measurement_time = measurements[0].measurement_time
    previous_measurement_time = current_measurement_time
    for analyte in measurements:
        time_diff = parser.parse(analyte.measurement_time) - parser.parse(
            previous_measurement_time
        )
        if time_diff > MAX_MEASUREMENT_TIME_GROUP_DIFFERENCE:
            current_measurement_time = analyte.measurement_time
        if analyte.name in groups[current_measurement_time]:
            if analyte.concentration_value is NaN:
                continue
            # NOTE: if this fails, it's probably because MAX_MEASUREMENT_TIME_GROUP_DIFFERENCE is too big
            # and we're erroneously grouping two groups of measurements into one.
            # We could potentially make this more robust by just splitting into a new group if a duplicate
            # measurement is found, but cross that bridge when we come to it.
            if (
                groups[current_measurement_time][analyte.name].concentration_value
                is not NaN
            ):
                msg = f"Duplicate measurement for {analyte.name} in the same measurement group: {analyte.concentration_value} vs {groups[current_measurement_time][analyte.name].concentration_value}"
                raise AllotropyParserError(msg)
        groups[current_measurement_time][analyte.name] = analyte
        previous_measurement_time = analyte.measurement_time

    return dict(groups)


@dataclass(frozen=True)
class Sample:
    name: str
    measurements: dict[str, dict[str, RawMeasurement]]
    batch: str | None = None

    @staticmethod
    def create(name: str, batch: str | None, sample_data: pd.DataFrame) -> Sample:
        return Sample(
            name,
            create_measurements(sample_data),
            batch=batch or None,
        )

    @staticmethod
    def create_samples(samples_data: pd.DataFrame) -> list[Sample]:
        return [
            Sample.create(name, batch, samples_data)
            for (name, batch), samples_data in samples_data.groupby(
                # A sample group is defined by both the sample and the batch identifier
                ["sample identifier", "batch identifier"]
            )
        ]


def _create_measurements(
    sample: Sample, measurement_time: str, raw_measurements: dict[str, RawMeasurement]
) -> list[Measurement]:
    measurements: list[Measurement] = []

    analytes: list[Analyte] = []
    for name in sorted(raw_measurements):
        measurement = raw_measurements[name]
        value = measurement.concentration_value
        # TODO: report value and add error
        if value is NaN:
            continue

        if name == OPTICAL_DENSITY:
            measurements.append(
                Measurement(
                    identifier=random_uuid_str(),
                    measurement_time=measurement_time,
                    sample_identifier=sample.name,
                    batch_identifier=sample.batch,
                    absorbance=value if isinstance(value, float) else -1,
                )
            )
        else:
            analytes.append(
                Analyte(
                    name=measurement.name,
                    value=value if isinstance(value, float) else -1,
                    unit=measurement.unit,
                )
            )

    if analytes:
        measurements.append(
            Measurement(
                identifier=random_uuid_str(),
                measurement_time=measurement_time,
                sample_identifier=sample.name,
                batch_identifier=sample.batch,
                analytes=analytes,
            )
        )

    return measurements


def create_measurement_groups(
    samples: list[Sample], title: Title
) -> list[MeasurementGroup]:
    groups: list[MeasurementGroup] = []
    for sample in samples:
        measurements = [
            measurement
            for measurement_time, sample_measurements in sample.measurements.items()
            for measurement in _create_measurements(
                sample, measurement_time, sample_measurements
            )
        ]
        if not measurements:
            continue
        groups.append(
            MeasurementGroup(
                analyst=title.analyst,
                data_processing_time=title.data_processing_time,
                measurements=measurements,
            )
        )
    return groups


def create_metadata(title: Title, file_path: str) -> Metadata:
    path = Path(file_path)
    return Metadata(
        file_name=path.name,
        unc_path=file_path,
        device_type=SOLUTION_ANALYZER,
        model_number=title.model_number,
        equipment_serial_number=title.device_serial_number,
        device_identifier=NOT_APPLICABLE,
        software_name=title.model_number,
        software_version=title.software_version,
        asm_file_identifier=path.with_suffix(".json").name,
        data_system_instance_identifier=NOT_APPLICABLE,
    )
