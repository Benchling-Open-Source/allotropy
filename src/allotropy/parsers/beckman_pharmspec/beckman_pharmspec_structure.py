from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.light_obscuration.benchling._2023._12.light_obscuration import (
    CalculatedDataItem,
    DataSource,
    Measurement,
    MeasurementGroup,
    Metadata,
    ProcessedData,
    ProcessedDataFeature,
)
from allotropy.parsers.beckman_pharmspec.constants import (
    PHARMSPEC_SOFTWARE_NAME,
    UNIT_LOOKUP,
    VALID_CALCS,
)
from allotropy.parsers.utils.pandas import (
    map_rows,
    SeriesData,
)
from allotropy.parsers.utils.uuids import random_uuid_str


def _create_processed_data(data: SeriesData) -> ProcessedDataFeature:
    return ProcessedDataFeature(
        identifier=random_uuid_str(),
        particle_size=data[float, "Particle Size(µm)"],
        cumulative_count=data[float, "Cumulative Count"],
        cumulative_particle_density=data[float, "Cumulative Counts/mL"],
        differential_particle_density=data.get(float, "Differential Counts/mL"),
        differential_count=data.get(float, "Differential Count"),
    )


@dataclass(frozen=True, kw_only=True)
class Distribution:
    name: str
    features: list[ProcessedDataFeature]
    is_calculated: bool

    @staticmethod
    def create(df: pd.DataFrame, name: str) -> Distribution:
        return Distribution(
            name=name,
            features=map_rows(df, _create_processed_data),
            is_calculated=name in VALID_CALCS,
        )

    @staticmethod
    def create_distributions(df: pd.DataFrame) -> list[Distribution]:
        distributions = []
        for g, gdf in df.groupby("Run No."):
            distributions.append(Distribution.create(gdf, str(g)))
        return distributions


@dataclass(frozen=True, kw_only=True)
class Header:
    measurement_time: str
    flush_volume_setting: float
    detector_view_volume: float
    repetition_setting: int
    sample_volume_setting: float
    sample_identifier: str
    dilution_factor_setting: float
    analyst: str
    equipment_serial_number: str
    detector_identifier: str
    detector_model_number: str
    software_version: str

    @staticmethod
    def _get_software_version_report_string(report_string: str) -> str:
        match = re.search(r"v(\d+(?:\.\d+)?(?:\.\d+)?)", report_string)
        if match:
            return match.group(1)
        return "Unknown"

    @staticmethod
    def create(data: SeriesData) -> Header:
        return Header(
            measurement_time=data[str, "Sample Date"].replace(".", "-"),
            flush_volume_setting=0,
            detector_view_volume=data[float, "View Volume"],
            repetition_setting=data[int, "No Of Runs"],
            sample_volume_setting=data[float, "Sample Volume (mL)"],
            sample_identifier=data[str, "Probe"],
            dilution_factor_setting=data[float, "Dilution Factor"],
            analyst=data[str, "Operator Name"],
            software_version=Header._get_software_version_report_string(
                data.series.iloc[0]
            ),
            equipment_serial_number=data[str, "Sensor Serial Number"],
            detector_identifier="",
            detector_model_number=data[str, "Sensor Model"],
        )


def create_metadata(header: Header, file_name: str) -> Metadata:
    return Metadata(
        file_name=file_name,
        software_name=PHARMSPEC_SOFTWARE_NAME,
        software_version=header.software_version,
        detector_identifier=header.detector_identifier,
        detector_model_number=header.detector_model_number,
        equipment_serial_number=header.equipment_serial_number,
    )


def create_measurement_groups(
    header: Header, distributions: list[Distribution]
) -> list[MeasurementGroup]:
    return [
        MeasurementGroup(
            analyst=header.analyst,
            measurements=[
                Measurement(
                    identifier=distribution.name,
                    measurement_time=header.measurement_time,
                    flush_volume_setting=header.flush_volume_setting,
                    detector_view_volume=header.detector_view_volume,
                    repetition_setting=header.repetition_setting,
                    sample_volume_setting=header.sample_volume_setting,
                    sample_identifier=header.sample_identifier,
                    processed_data=ProcessedData(
                        dilution_factor_setting=header.dilution_factor_setting,
                        distributions=distribution.features,
                    ),
                )
                for distribution in [x for x in distributions if not x.is_calculated]
            ],
        )
    ]


def create_calculated_data(
    distributions: list[Distribution],
) -> list[CalculatedDataItem]:
    particle_size_sources = defaultdict(list)
    for source in [
        feature
        for distribution in distributions
        if not distribution.is_calculated
        for feature in distribution.features
    ]:
        particle_size_sources[source.particle_size].append(source)

    return [
        CalculatedDataItem(
            identifier=random_uuid_str(),
            name=f"{distribution.name}_{name}".lower(),
            value=value,
            unit=UNIT_LOOKUP[name],
            data_sources=[
                DataSource(
                    identifier=x.identifier,
                    feature=name.replace("_", " "),
                )
                for x in particle_size_sources[feature.particle_size]
            ],
        )
        for distribution in distributions
        for feature in distribution.features
        if distribution.is_calculated
        # Ignore "identifier" attribute, and skip empty values
        for name, value in feature.__dict__.items()
        if name != "identifier" and value is not None
    ]
