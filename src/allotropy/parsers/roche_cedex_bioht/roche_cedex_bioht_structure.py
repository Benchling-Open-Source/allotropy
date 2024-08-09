# mypy: disallow_any_generics = False

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from dateutil import parser
import pandas as pd

from allotropy.exceptions import AllotropyParserError
from allotropy.parsers.roche_cedex_bioht.constants import (
    MAX_MEASUREMENT_TIME_GROUP_DIFFERENCE,
)
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_reader import (
    RocheCedexBiohtReader,
)
from allotropy.parsers.utils.pandas import map_rows, SeriesData


@dataclass(frozen=True)
class Title:
    data_processing_time: str
    analyst: str
    device_serial_number: str
    model_number: str | None

    @staticmethod
    def create(title_data: SeriesData) -> Title:
        return Title(
            title_data[str, "data processing time"],
            title_data[str, "analyst"],
            title_data[str, "device serial number"],
            title_data.get(str, "model number"),
        )


@dataclass(frozen=True)
class Measurement:
    name: str
    measurement_time: str
    concentration_value: float | None = None
    unit: str | None = None

    @staticmethod
    def create(data: SeriesData) -> Measurement:
        return Measurement(
            data[str, "analyte name"],
            data[str, "measurement time"],
            data.get(float, "concentration value"),
            data.get(str, "concentration unit"),
        )


def create_measurements(data: pd.DataFrame) -> dict[str, dict[str, Measurement]]:
    measurements = sorted(
        map_rows(data, Measurement.create), key=lambda a: a.measurement_time
    )

    # Dict from measurement time to data
    groups: defaultdict[str, dict[str, Measurement]] = defaultdict(dict)

    current_measurement_time = measurements[0].measurement_time
    previous_measurement_time = current_measurement_time
    for analyte in measurements:
        time_diff = parser.parse(analyte.measurement_time) - parser.parse(
            previous_measurement_time
        )
        if time_diff > MAX_MEASUREMENT_TIME_GROUP_DIFFERENCE:
            current_measurement_time = analyte.measurement_time
        if analyte.name in groups[current_measurement_time]:
            if analyte.concentration_value is None:
                continue
            # NOTE: if this fails, it's probably because MAX_MEASUREMENT_TIME_GROUP_DIFFERENCE is too big
            # and we're erroneously grouping two groups of measurements into one.
            # We could potentially make this more robust by just splitting into a new group if a duplicate
            # measurement is found, but cross that bridge when we come to it.
            if (
                groups[current_measurement_time][analyte.name].concentration_value
                is not None
            ):
                msg = f"Duplicate measurement for {analyte.name} in the same measurement group."
                raise AllotropyParserError(msg)
        groups[current_measurement_time][analyte.name] = analyte
        previous_measurement_time = analyte.measurement_time

    return dict(groups)


@dataclass(frozen=True)
class Sample:
    name: str
    measurements: dict[str, dict[str, Measurement]]
    batch: str | None = None

    @staticmethod
    def create(name: str, batch: str | None, sample_data: pd.DataFrame) -> Sample:
        return Sample(
            name,
            create_measurements(sample_data),
            batch=batch or None,
        )


@dataclass(frozen=True)
class Data:
    title: Title
    samples: list[Sample]

    @staticmethod
    def create(reader: RocheCedexBiohtReader) -> Data:
        return Data(
            title=Title.create(reader.title_data),
            samples=[
                Sample.create(name, batch, samples_data)
                for (name, batch), samples_data in reader.samples_data.groupby(
                    # A sample group is defined by both the sample and the batch identifier
                    ["sample identifier", "batch identifier"]
                )
            ],
        )
