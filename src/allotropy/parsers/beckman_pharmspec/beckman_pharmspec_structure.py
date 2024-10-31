from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
from pathlib import Path
import re

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.solution_analyzer.rec._2024._09.solution_analyzer import (
    CalculatedDataItem,
    DataProcessing,
    DataSource,
    DistributionDocument,
    Error,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.beckman_pharmspec.constants import (
    DEVICE_TYPE,
    PHARMSPEC_SOFTWARE_NAME,
    REQUIRED_DISTRIBUTION_DOCUMENT_KEYS,
    UNIT_LOOKUP,
    VALID_CALCS,
)
from allotropy.parsers.constants import NEGATIVE_ZERO, NOT_APPLICABLE
from allotropy.parsers.utils.pandas import (
    map_rows,
    SeriesData,
)
from allotropy.parsers.utils.uuids import random_uuid_str

ZERO_FLOAT = 0.0


def _create_processed_data(data: SeriesData) -> DistributionDocument:

    return DistributionDocument(
        distribution_identifier=random_uuid_str(),
        particle_size=data[float, "Particle Size(µm)"],
        cumulative_count=data[float, "Cumulative Count"],
        cumulative_particle_density=data[float, "Cumulative Counts/mL"],
        differential_particle_density=data.get(
            float, "Differential Counts/mL", NEGATIVE_ZERO
        ),
        differential_count=data.get(float, "Differential Count", NEGATIVE_ZERO),
    )


@dataclass(frozen=True, kw_only=True)
class Distribution:
    name: str
    features: list[DistributionDocument]
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
        )


def create_metadata(header: Header, file_path: str) -> Metadata:
    path = Path(file_path)
    return Metadata(
        file_name=path.name,
        unc_path=file_path,
        software_name=PHARMSPEC_SOFTWARE_NAME,
        software_version=header.software_version,
        equipment_serial_number=header.equipment_serial_number,
        asm_file_identifier=path.with_suffix(".json").name,
        data_system_instance_identifier=NOT_APPLICABLE,
        flush_volume_setting=header.flush_volume_setting,
        detector_view_volume=header.detector_view_volume,
        repetition_setting=header.repetition_setting,
        sample_volume_setting=header.sample_volume_setting,
        device_type=DEVICE_TYPE,
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
                    sample_identifier=header.sample_identifier,
                    data_processing=DataProcessing(
                        dilution_factor_setting=header.dilution_factor_setting,
                    ),
                    distribution_documents=distribution.features,
                    errors=[
                        Error(
                            error=NOT_APPLICABLE,
                            feature=f"{key.replace('_', ' ')} - {feature.distribution_identifier}",
                        )
                        for feature in distribution.features
                        for key in feature.__dict__.keys()
                        if key in REQUIRED_DISTRIBUTION_DOCUMENT_KEYS
                        and is_negative_zero(feature.__dict__[key])
                    ],
                )
                for distribution in [x for x in distributions if not x.is_calculated]
            ],
            data_processing_time=header.measurement_time,
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
                    identifier=x.distribution_identifier,
                    feature=name.replace("_", " "),
                )
                for x in particle_size_sources[feature.particle_size]
            ],
        )
        for distribution in distributions
        for feature in distribution.features
        if distribution.is_calculated
        # Ignore "distribution_identifier" attribute, and skip empty or -0.0 values
        for name, value in feature.__dict__.items()
        if name != "distribution_identifier"
        and value is not None
        and not is_negative_zero(value)
    ]


def is_negative_zero(x: float) -> bool:
    return x == ZERO_FLOAT and math.copysign(1, x) == -1
