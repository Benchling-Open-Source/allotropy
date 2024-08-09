# mypy: disallow_any_generics = False

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

from dateutil import parser
import pandas as pd

from allotropy.parsers.roche_cedex_bioht.constants import (
    MOLAR_CONCENTRATION_CLS_BY_UNIT,
    NON_AGGREGABLE_PROPERTIES,
)
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_reader import (
    RocheCedexBiohtReader,
)
from allotropy.parsers.utils.pandas import SeriesData


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
class Analyte:
    name: str
    measurement_time: str
    concentration_value: float | None
    unit: str | None

    @staticmethod
    def create(data: pd.Series) -> Analyte:
        analyte_name: str = data.get("analyte name")  # type: ignore[assignment]
        measurement_time: str = data.get("measurement time")  # type: ignore[assignment]
        concentration_value: float | None = data.get("concentration value")  # type: ignore[assignment]
        unit: str | None = data.get("concentration unit")  # type: ignore[assignment]

        return Analyte(analyte_name, measurement_time, concentration_value, unit)


@dataclass(frozen=True)
class AnalyteList:
    measurements: dict[str, dict[str, Analyte]]

    @staticmethod
    def create(data: pd.DataFrame) -> AnalyteList:
        analytes = [Analyte.create(analyte_data) for _, analyte_data in data.iterrows()]
        analytes = sorted(analytes, key=lambda a: a.measurement_time)

        # Dict from measurement time to data
        measurements = defaultdict(dict)

        current_measurement_time = analytes[0].measurement_time
        previous_measurement_time = current_measurement_time
        for analyte in analytes:
            time_diff = parser.parse(analyte.measurement_time) - parser.parse(previous_measurement_time)
            if time_diff > timedelta(minutes=5):
                current_measurement_time = analyte.measurement_time
            if analyte.concentration_value is None and analyte.name in measurements[current_measurement_time]:
                continue
            measurements[current_measurement_time][analyte.name] = analyte
            previous_measurement_time = analyte.measurement_time

        return AnalyteList(measurements)

        molar_concentration_dict = defaultdict(list)
        molar_concentration_nans = {}
        non_aggregrable_dict = defaultdict(list)
        non_aggregable_nans = {}
        num_measurement_docs = 1

        for analyte in analytes:
            analyte_name = analyte.name
            concentration_value = analyte.concentration_value

            if analyte_cls := NON_AGGREGABLE_PROPERTIES.get(analyte_name):
                if concentration_value is None:
                    non_aggregable_nans[analyte_name] = analyte_cls(
                        value=concentration_value
                    )
                else:
                    non_aggregrable_dict[analyte_name].append(
                        analyte_cls(value=concentration_value)
                    )

                num_measurement_docs = max(
                    len(non_aggregrable_dict[analyte_name]), num_measurement_docs
                )
            else:
                unit = analyte.unit
                if unit is None:
                    continue

                molar_concentration_item_cls = MOLAR_CONCENTRATION_CLS_BY_UNIT.get(unit)
                if molar_concentration_item_cls is None:
                    continue

                molar_concentration_item = molar_concentration_item_cls(
                    value=concentration_value
                )
                if concentration_value is None:
                    molar_concentration_nans[analyte_name] = molar_concentration_item
                else:
                    molar_concentration_dict[analyte_name].append(
                        molar_concentration_item
                    )
                num_measurement_docs = max(
                    len(molar_concentration_dict[analyte_name]), num_measurement_docs
                )

        # Only include None values if there is not a valid value for that analyte
        for analyte_name in non_aggregable_nans:
            if len(non_aggregrable_dict[analyte_name]) == 0:
                non_aggregrable_dict[analyte_name].append(
                    non_aggregable_nans[analyte_name]
                )
                num_measurement_docs = max(
                    len(non_aggregrable_dict[analyte_name]), num_measurement_docs
                )

        for analyte_name in molar_concentration_nans:
            if len(molar_concentration_dict[analyte_name]) == 0:
                molar_concentration_dict[analyte_name].append(
                    molar_concentration_nans[analyte_name]
                )
                num_measurement_docs = max(
                    len(molar_concentration_dict[analyte_name]), num_measurement_docs
                )

        return AnalyteList(
            analytes,
            molar_concentration_dict,
            molar_concentration_nans,
            non_aggregrable_dict,
            non_aggregable_nans,
            num_measurement_docs,
        )


@dataclass(frozen=True)
class Sample:
    name: str
    analyte_list: AnalyteList
    batch: str | None = None

    @staticmethod
    def create(name: str, batch: str | None, sample_data: pd.DataFrame) -> Sample:
        return Sample(
            name,
            AnalyteList.create(sample_data),
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
                Sample.create(name, batch, samples_data.sort_values(by="analyte name"))
                for (name, batch), samples_data in reader.samples_data.groupby(
                    # A sample group is defined by both the sample and the batch identifier
                    ["sample identifier", "batch identifier"]
                )
            ],
        )
