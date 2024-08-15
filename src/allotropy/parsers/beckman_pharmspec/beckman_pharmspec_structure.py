from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.light_obscuration.benchling._2023._12.light_obscuration import (
    CalculatedDataItem,
    Data,
    DataSource,
    Measurement,
    MeasurementGroup,
    Metadata,
    ProcessedData,
    ProcessedDataFeature,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_pharmspec.constants import (
    PHARMSPEC_SOFTWARE_NAME,
    UNIT_LOOKUP,
    VALID_CALCS,
)
from allotropy.parsers.utils.pandas import map_rows, read_excel, SeriesData
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


def _create_calculated_data(
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


def _extract_data(df: pd.DataFrame) -> tuple[pd.DataFrame, SeriesData]:
    """Find the data in the raw dataframe. We identify the boundary of the data
    by finding the index first row which contains the word 'Particle' and ending right before
    the index of the first row containing 'Approver'.
    """
    start = df[df[1].str.contains("Particle", na=False)].index.values[0]
    end = df[df[0].str.contains("Approver_", na=False)].index.values[0] - 1

    # The header data is everything up to the start of the data.
    # It is stored in two columns spread over the first 6 columns.
    raw_header = df.loc[: start - 1].T
    header_data = pd.concat([raw_header.loc[2], raw_header.loc[5]])
    header_columns = pd.concat([raw_header.loc[0], raw_header.loc[3]])
    header_data.index = pd.Index(header_columns)
    header = SeriesData(header_data)

    data = df.loc[start:end, :]
    data = data.dropna(how="all").dropna(how="all", axis=1)
    data[0] = data[0].ffill()
    data = data.dropna(subset=1).reset_index(drop=True)
    data.columns = pd.Index([str(x).strip() for x in data.loc[0]])
    data = data.loc[1:, :]

    return data, header


def create_data(named_file_contents: NamedFileContents) -> Data:
    df = read_excel(named_file_contents.contents, header=None, engine="calamine")
    dist_data, header_data = _extract_data(df)
    distributions = Distribution.create_distributions(dist_data)
    header = Header.create(header_data)

    return Data(
        Metadata(
            file_name=named_file_contents.original_file_name,
            software_name=PHARMSPEC_SOFTWARE_NAME,
            software_version=header.software_version,
            detector_identifier=header.detector_identifier,
            detector_model_number=header.detector_model_number,
            equipment_serial_number=header.equipment_serial_number,
        ),
        measurement_groups=[
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
                    for distribution in [
                        x for x in distributions if not x.is_calculated
                    ]
                ],
            )
        ],
        calculated_data=_create_calculated_data(distributions),
    )
