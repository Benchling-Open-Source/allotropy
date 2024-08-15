from __future__ import annotations

from dataclasses import dataclass
import re

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.light_obscuration._2023._12.light_obscuration import (
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
from allotropy.parsers.beckman_pharmspec.constants import PHARMSPEC_SOFTWARE_NAME
from allotropy.parsers.utils.pandas import map_rows, read_excel, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str

# This map is used to coerce the column names coming in the raw data
# into names of the allotrope properties.
UNIT_LOOKUP = {
    "particle_size": "μm",
    "cumulative_count": "(unitless)",
    "cumulative_particle_density": "Counts/mL",
    "differential_particle_density": "Counts/mL",
    "differential_count": "(unitless)",
}


VALID_CALCS = ["Average"]


@staticmethod
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
    data: list[ProcessedDataFeature]
    is_calculated: bool

    @staticmethod
    def create(df: pd.DataFrame, name: str) -> Distribution:
        return Distribution(
            name=name,
            data=map_rows(df, _create_processed_data),
            is_calculated=name in VALID_CALCS,
        )


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
            software_version=Header._get_software_version_report_string(data.series.iloc[0]),
            equipment_serial_number=data[str, "Sensor Serial Number"],
            detector_identifier="",
            detector_model_number=data[str, "Sensor Model"],
        )


@dataclass(frozen=True, kw_only=True)
class PharmSpecData:
    header: Header
    distributions: list[Distribution]

    @staticmethod
    def _get_data_using_key_bounds(
        df: pd.DataFrame, start_key: str, end_key: str
    ) -> tuple[pd.DataFrame, SeriesData]:
        """Find the data in the raw dataframe. We identify the boundary of the data
        by finding the index first row which contains the word 'Particle' and ending right before
        the index of the first row containing 'Approver'.

        :param df: the raw dataframe
        :param start_key: the key to start the slice
        :parm end_key: the key to end the slice
        :return: the dataframe slice between the start and end bounds
        """
        start = df[df[1].str.contains(start_key, na=False)].index.values[0]
        end = df[df[0].str.contains(end_key, na=False)].index.values[0] - 1
        raw_header = df.loc[:start - 1].T
        header = pd.concat([raw_header.loc[2], raw_header.loc[5]])
        header_columns = pd.concat([raw_header.loc[0], raw_header.loc[3]])
        header.index = pd.Index(header_columns)

        return df.loc[start:end, :], SeriesData(header)

    @staticmethod
    def _extract_data(df: pd.DataFrame) -> tuple[pd.DataFrame, SeriesData]:
        """Extract the Average data frame from the raw data. Initial use cases have focused on
        only extracting the Average data, not the individual runs. The ASM does support multiple
        Distribution objects, but they don't have names, so it's not possible to pick these out
        after the fact. As such, this extraction only includes the Average data.

        :param df: the raw dataframe
        :return: the average data frame
        """
        data, header = PharmSpecData._get_data_using_key_bounds(
            df, start_key="Particle", end_key="Approver_"
        )
        data = data.dropna(how="all").dropna(how="all", axis=1)
        data[0] = data[0].ffill()
        data = data.dropna(subset=1).reset_index(drop=True)
        data.columns = pd.Index([str(x).strip() for x in data.loc[0]])
        data = data.loc[1:, :]
        return data, header

    @staticmethod
    def _create_distributions(df: pd.DataFrame) -> list[Distribution]:
        distributions = []
        for g, gdf in df.groupby("Run No."):
            distributions.append(Distribution.create(gdf, str(g)))
        return distributions

    @staticmethod
    def create(df: pd.DataFrame) -> PharmSpecData:
        data, header = PharmSpecData._extract_data(df)
        return PharmSpecData(
            header=Header.create(header),
            distributions=PharmSpecData._create_distributions(data),
        )


def _create_calculated_data(data: PharmSpecData):
    calcs = [x for x in data.distributions if x.is_calculated]
    sources = [x for x in data.distributions if not x.is_calculated]

    calculated_data: list[CalculatedDataItem] = []

    for distribution in calcs:
        for row in distribution.data:
            for name, unit in UNIT_LOOKUP.items():
                value = getattr(row, name, None)
                if value is None:
                    continue
                source_rows = [
                    x
                    for source in sources
                    for x in source.data
                    if row.particle_size == x.particle_size
                ]
                calculated_data.append(
                    CalculatedDataItem(
                        identifier=random_uuid_str(),
                        name=f"{distribution.name}_{name}".lower(),
                        value=value,
                        unit=unit,
                        data_sources=[
                            DataSource(
                                identifier=x.identifier,
                                feature=name.replace("_", " "),
                            )
                            for x in source_rows
                        ]
                    ),
                )

    return calculated_data


def create_data(named_file_contents: NamedFileContents) -> Data:
    df = read_excel(named_file_contents.contents, header=None, engine="calamine")
    data = PharmSpecData.create(df)

    return Data(
        Metadata(
            file_name=named_file_contents.original_file_name,
            software_name=PHARMSPEC_SOFTWARE_NAME,
            software_version=data.header.software_version,
            detector_identifier=data.header.detector_identifier,
            detector_model_number=data.header.detector_model_number,
            equipment_serial_number=data.header.equipment_serial_number,
        ),
        measurement_groups=[
            MeasurementGroup(
                analyst=data.header.analyst,
                measurements=[
                    Measurement(
                        identifier=distribution.name,
                        measurement_time=data.header.measurement_time,
                        flush_volume_setting=data.header.flush_volume_setting,
                        detector_view_volume=data.header.detector_view_volume,
                        repetition_setting=data.header.repetition_setting,
                        sample_volume_setting=data.header.sample_volume_setting,
                        sample_identifier=data.header.sample_identifier,
                        processed_data=ProcessedData(
                            dilution_factor_setting=data.header.dilution_factor_setting,
                            distributions=distribution.data,
                        )
                    )
                    for distribution in [x for x in data.distributions if not x.is_calculated]
                ]
            )
        ],
        calculated_data=_create_calculated_data(data),
    )
