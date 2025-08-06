from __future__ import annotations
import re
from attr import dataclass
import pandas as pd
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueHertz,
    TQuantityValueNumber,
)
from allotropy.allotrope.schema_mappers.adm.binding_affinity_analyzer.benchling._2024._12.binding_affinity_analyzer import (
    Measurement,
    MeasurementGroup,
    Metadata,
)
from pathlib import Path
from allotropy.parsers.cytiva_biacore_insight import constants
from allotropy.parsers.cytiva_biacore_insight.cytiva_biacore_insight_reader import (
    CytivaBiacoreInsightReader,
)
from allotropy.parsers.utils.pandas import (
    SeriesData,
    df_to_series_data,
    parse_header_row,
    split_dataframe,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import quantity_or_none, try_float


@dataclass(frozen=True)
class RunMetadata:
    sensor_chip_id: str
    sensor_chip_type: str
    lot_number: str
    model_number: str
    equipment_serial_number: str
    measurement_time: str
    number_of_cycles: float
    data_collection_rate: float
    running_buffer: str
    measurement_end_time: str
    method_name: str
    compartment_temperature: float | None
    run_table: pd.DataFrame

    @staticmethod
    def create_runs(runs_data: pd.DataFrame) -> list[RunMetadata]:
        runs_data = runs_data.reset_index(drop=True)
        run, rest = split_dataframe(
            runs_data, lambda row: str(row[0]).startswith("Run")
        )
        runs = [run]
        while rest is not None:
            run, rest = split_dataframe(rest, lambda row: str(row[0]).startswith("Run"))
            runs.append(run)
        return [RunMetadata.create(run) for run in runs if not run.empty]

    @staticmethod
    def create(run_data: pd.DataFrame) -> RunMetadata:
        def get_run_information(idx: int) -> SeriesData:
            idx1, idx2 = idx + 1, idx + 4
            rd1 = run_data.loc[idx1:idx2][[3, 4]].rename(columns={3: "n", 4: "v"})
            rd2 = run_data.loc[idx1:idx2][[6, 7]].rename(columns={6: "n", 7: "v"})
            rd3 = run_data.loc[idx1:idx2][[10, 11]].rename(columns={10: "n", 11: "v"})
            return df_to_series_data(parse_header_row(pd.concat((rd1, rd2, rd3)).T))

        run_table_start = 0
        chip_data = SeriesData()
        run_information = SeriesData()
        run_table = pd.DataFrame()
        compartment_temperature = None
        for idx, row in run_data.iterrows():
            if row[0] == "Chip information":
                chip_data = df_to_series_data(
                    parse_header_row(run_data.loc[idx + 1 : idx + 4][[0, 1]].T)
                )
                run_information = get_run_information(idx)
            elif row[0] == "Flow cell":
                run_table_start = idx
            elif row[0] == "Method summary":
                run_table = (
                    parse_header_row(run_data.loc[run_table_start : idx - 1])
                    .dropna(how="all")
                    .reset_index(drop=True)
                )
                run_table = run_table.loc[:, ~run_table.columns.str.contains("^nan$")]
            elif row[0] == "Set temperatures 1":
                if match := re.match(constants.COMPARTMENT_TEMP_REGEX, row[1]):
                    compartment_temperature = float(match.group(1))

        return RunMetadata(
            sensor_chip_id=chip_data[str, "Chip id"],
            sensor_chip_type=chip_data[str, "Chip type"],
            lot_number=chip_data[str, "Lot number"],
            model_number=run_information[str, "Instrument type"],
            equipment_serial_number=run_information[str, "Instrument id"],
            measurement_time=run_information[str, "Start"],
            number_of_cycles=run_information[float, "Cycles"],
            data_collection_rate=run_information[float, "Data collection rate"],
            running_buffer=run_information[str, "Running buffer"],
            measurement_end_time=run_information[str, "End"],
            method_name=run_information[str, "Method"],
            compartment_temperature=compartment_temperature,
            run_table=run_table,
        )


@dataclass(frozen=True)
class BiacoreInsightMetadata:
    product_manufacturer: str
    file_name: str
    unc_path: str
    software_name: str
    software_version: str
    analyst: str
    analytical_method_id: str
    runs: list[RunMetadata]

    @staticmethod
    def create(reader: CytivaBiacoreInsightReader) -> BiacoreInsightMetadata:
        properties = reader.data["Properties"]
        properties, runs_data = split_dataframe(
            properties, lambda row: str(row[0]).startswith("Run")
        )
        for idx, row in properties.iterrows():
            if row[0] == "Evaluation":
                evaluation_data = df_to_series_data(
                    parse_header_row(properties.loc[idx + 1 : idx + 4][[0, 1]].T)
                )
                # If the "Name" column is not at index 3, it indicates that there are multiple runs
                # the data for the first run starts at index 4. We only need the first run's data.
                # Since the "created by" property is the same for all runs,
                if properties.at[idx + 1, 3] == "Name":
                    ncol, vcol = 3, 4
                else:
                    ncol, vcol = 4, 5
                runs_this_evaluation = df_to_series_data(
                    parse_header_row(properties.loc[idx + 1 : idx + 4][[ncol, vcol]].T)
                )
            elif row[0] == "Software":
                software_data = df_to_series_data(
                    parse_header_row(properties.loc[idx + 1 : idx + 2][[0, 1]].T)
                )

        return BiacoreInsightMetadata(
            # TODO: validate this is the correct way to get the product manufacturer (and not the constants.PRODUCT_MANUFACTURER)
            product_manufacturer=runs_this_evaluation[str, "Created by"],
            file_name=evaluation_data[str, "Name"],
            unc_path=evaluation_data[str, "Path"],
            software_name=software_data[str, "Name"],
            software_version=software_data[str, "Version"],
            analyst=evaluation_data[str, "Modified by"],
            analytical_method_id=evaluation_data[str, "Name"],
            runs=RunMetadata.create_runs(runs_data),
        )


@dataclass(frozen=True)
class Measurement:
    measurement_identifier: str
    sample_identifier: str
    viability: float


@dataclass(frozen=True)
class Data:
    metadata: BiacoreInsightMetadata
    measurements: list[Measurement]

    @staticmethod
    def create(reader: CytivaBiacoreInsightReader) -> Data:

        return Data(
            metadata=BiacoreInsightMetadata.create(reader),
        )


def create_metadata(metadata: BiacoreInsightMetadata, file_path: str) -> Metadata:
    path = Path(file_path)
    first_run = metadata.runs[0]
    return Metadata(
        device_identifier=constants.DEVICE_IDENTIFIER,
        asm_file_identifier=path.with_suffix(".json").name,
        model_number=metadata.model_number,
        sensor_chip_identifier=first_run.sensor_chip_id,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        software_name=metadata.software_name,
        software_version=metadata.software_version,
        file_name=metadata.file_name,
        unc_path=metadata.unc_path,
        detection_type=constants.DETECTION_TYPE,
        equipment_serial_number=metadata.equipment_serial_number,
        compartment_temperature=first_run.compartment_temperature,
        sensor_chip_type=first_run.sensor_chip_type,
        lot_number=first_run.lot_number,
    )


def create_measurement_groups(data: Data) -> list[MeasurementGroup]:
    # Here we assume that the first run contains the relevant metadata for the measurement group.
    run_metadata = data.metadata.runs[0]
    return [
        MeasurementGroup(
            measurement_time=run_metadata.measurement_time,
            analytical_method_identifier=data.metadata.analytical_method_id,
            analyst=data.metadata.analyst,
            measurement_aggregate_custom_info={
                "number_of_cycles": TQuantityValueNumber(
                    value=run_metadata.number_of_cycles
                ),
                "data_collection_rate": TQuantityValueHertz(
                    value=run_metadata.data_collection_rate
                ),
                "running_buffer": TQuantityValueHertz(
                    value=run_metadata.running_buffer
                ),
                "measurement_end_time": run_metadata.measurement_end_time,
            },
            measurements=[
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    sample_identifier=data[str, "Sample ID"],
                    viability=data[float, "Viability"],
                )
                for measurement in data.measurements
            ],
        )
    ]
