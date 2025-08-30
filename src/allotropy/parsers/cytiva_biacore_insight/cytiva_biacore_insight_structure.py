from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from attr import dataclass
import numpy as np
import pandas as pd

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDalton,
    TQuantityValueHertz,
    TQuantityValueMicroliterPerMinute,
    TQuantityValueNanomolar,
    TQuantityValueNumber,
    TQuantityValueResonanceUnits,
    TQuantityValueSecondTime,
    TQuantityValueSquareResonanceUnits,
    TQuantityValueUnitless,
)
from allotropy.allotrope.schema_mappers.adm.binding_affinity_analyzer.benchling._2024._12.binding_affinity_analyzer import (
    DeviceControlDocument,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ReportPoint,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.cytiva_biacore_insight import constants
from allotropy.parsers.cytiva_biacore_insight.cytiva_biacore_insight_reader import (
    CytivaBiacoreInsightReader,
)
from allotropy.parsers.utils.pandas import (
    df_to_series_data,
    drop_df_rows_while,
    map_rows,
    parse_header_row,
    SeriesData,
    split_dataframe,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    quantity_or_none,
)
from allotropy.types import DictType


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
        if len(runs) > 1:
            msg = "Instrument file contains multiple runs. Only single runs are supported at the moment."
            raise AllotropeConversionError(msg)
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
        for index, row in run_data.iterrows():
            idx = int(str(index))
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
    file_name: str
    unc_path: str
    software_name: str
    software_version: str
    analyst: str
    analytical_method_id: str
    runs: list[RunMetadata]
    data_processing_document: DictType | None = None

    @staticmethod
    def create(reader: CytivaBiacoreInsightReader) -> BiacoreInsightMetadata:

        properties = reader.data["Properties"]
        properties, runs_data = split_dataframe(
            properties, lambda row: str(row[0]).startswith("Run")
        )
        if runs_data is None or runs_data.empty:
            msg = "No run data found in the properties section of instrument file."
            raise AllotropeConversionError(msg)
        for index, row in properties.iterrows():
            idx = int(str(index))
            if row[0] == "Evaluation":
                evaluation_data = df_to_series_data(
                    parse_header_row(properties.loc[idx + 1 : idx + 4][[0, 1]].T)
                )
            elif row[0] == "Software":
                software_data = df_to_series_data(
                    parse_header_row(properties.loc[idx + 1 : idx + 2][[0, 1]].T)
                )

        data_processing_doc = BiacoreInsightMetadata.get_data_processing_doc(reader)

        return BiacoreInsightMetadata(
            file_name=evaluation_data[str, "Name"],
            unc_path=evaluation_data[str, "Path"],
            software_name=software_data[str, "Name"],
            software_version=software_data[str, "Version"],
            analyst=evaluation_data[str, "Modified by"],
            analytical_method_id=evaluation_data[str, "Name"],
            runs=RunMetadata.create_runs(runs_data),
            data_processing_document=data_processing_doc,
        )

    @staticmethod
    def get_data_processing_doc(reader: CytivaBiacoreInsightReader) -> DictType | None:
        table_names = [
            "QC - Capture baseline",
            "QC - Capture level",
            "QC - Binding to reference",
        ]
        qc_tables = [table for table in table_names if table in reader.data]
        qc_df = None
        while qc_df is None and qc_tables:
            qc_table = qc_tables.pop(0)
            _, qc_df = split_dataframe(
                reader.data[qc_table],
                lambda row: row[0] == "Blank subtraction",
                include_split_row=True,
            )

        if qc_df is None or qc_df.empty:
            return None

        qc_metadata = df_to_series_data(
            parse_header_row(qc_df.dropna(how="all", axis=0).T[0:2])
        )
        metadata_keys = [
            "Blank subtraction",
            "Molecular weight adjustment",
            "Capture/ligand adjustment",
            "Adjustment for controls",
            "Curve analysis",
        ]
        return {key: qc_metadata.get(str, key) for key in metadata_keys}


@dataclass(frozen=True)
class Data:
    metadata: BiacoreInsightMetadata
    cycles: dict[int, list[Measurement]]

    @staticmethod
    def create(reader: CytivaBiacoreInsightReader) -> Data:
        metadata = BiacoreInsightMetadata.create(reader)
        return Data(
            metadata=metadata,
            cycles={
                cycle: _create_measurements_for_cycle(cycle, metadata, reader)
                for cycle in range(1, int(metadata.runs[0].number_of_cycles) + 1)
            },
        )


def create_metadata(metadata: BiacoreInsightMetadata, file_path: str) -> Metadata:
    path = Path(file_path)
    run_metadata = metadata.runs[0]
    return Metadata(
        device_identifier=constants.DEVICE_IDENTIFIER,
        asm_file_identifier=path.with_suffix(".json").name,
        data_system_instance_identifier=NOT_APPLICABLE,
        model_number=run_metadata.model_number,
        sensor_chip_identifier=run_metadata.sensor_chip_id,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        software_name=metadata.software_name,
        software_version=metadata.software_version,
        file_name=metadata.file_name,
        unc_path=metadata.unc_path,
        detection_type=constants.DETECTION_TYPE,
        equipment_serial_number=run_metadata.equipment_serial_number,
        compartment_temperature=run_metadata.compartment_temperature,
        sensor_chip_type=run_metadata.sensor_chip_type,
        lot_number=run_metadata.lot_number,
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
                "running_buffer": run_metadata.running_buffer,
                "measurement_end_time": run_metadata.measurement_end_time,
            },
            measurements=measurements,
        )
        for measurements in data.cycles.values()
    ]


@dataclass(frozen=True)
class KineticsData:
    acceptance_state: str | None
    curve_markers: str | None
    kinetics_model: str | None
    binding_on_rate_measurement_datum: float | None
    binding_off_rate_measurement_datum: float | None
    equilibrium_dissociation_constant: float | None
    maximum_binding_capacity: float | None
    kinetics_chi_squared: float | None
    tc: float | None

    @staticmethod
    def create(kinetics_data: SeriesData) -> KineticsData:
        return KineticsData(
            acceptance_state=kinetics_data.get(str, "Acceptance state"),
            curve_markers=kinetics_data.get(str, "Curve markers"),
            kinetics_model=kinetics_data.get(str, "Kinetics model"),
            binding_on_rate_measurement_datum=kinetics_data.get(float, "ka (1/Ms)"),
            binding_off_rate_measurement_datum=kinetics_data.get(float, "kd (1/s)"),
            equilibrium_dissociation_constant=kinetics_data.get(float, "KD (M)"),
            maximum_binding_capacity=kinetics_data.get(float, "Rmax (RU)"),
            kinetics_chi_squared=kinetics_data.get(float, "Kinetics Chi² (RU²)"),
            tc=kinetics_data.get(float, "tc"),
        )


class EvaluationKinetics:
    _data: dict[str, KineticsData]

    def __init__(self, kinetics_table: pd.DataFrame) -> None:
        self._data = {
            f'{row["Channel"]} {row["Capture 1 Solution"]} {row["Analyte 1 Solution"]}': KineticsData.create(
                SeriesData(row)
            )
            for _, row in kinetics_table.iterrows()
        }

    def get_data(
        self, channel: int, capture_solution: str, analyte_solution: str
    ) -> KineticsData | None:
        return self._data.get(f"{channel} {capture_solution} {analyte_solution}")


def _create_measurements_for_cycle(
    cycle_number: int,
    metadata: BiacoreInsightMetadata,
    reader: CytivaBiacoreInsightReader,
) -> list[Measurement]:
    # Report point table is the entry point
    report_point_table = _get_table_from_dataframe(
        reader.data["Report point table"], split_on="Run"
    )
    cycle_data = report_point_table[report_point_table["Cycle"] == cycle_number]
    evaluation_kinetics_table = _get_table_from_dataframe(
        reader.data["Evaluation - Kinetics"], split_on="Group"
    )
    evaluation_kinetics = EvaluationKinetics(evaluation_kinetics_table)

    return [
        create_measurement(channel_data, metadata, evaluation_kinetics)
        for _, channel_data in cycle_data.groupby("Channel")
    ]


def _get_table_from_dataframe(df: pd.DataFrame, split_on: str) -> pd.DataFrame:
    data_table = drop_df_rows_while(df, lambda row: row[0] != split_on)
    return parse_header_row(
        assert_not_none(data_table).replace(np.nan, None)
    ).reset_index(drop=True)


def create_measurement(
    channel_data: pd.DataFrame,
    metadata: BiacoreInsightMetadata,
    evaluation_kinetics: EvaluationKinetics,
) -> Measurement:
    run_metadata = metadata.runs[0]
    first_row_data = SeriesData(channel_data.iloc[0])
    run = first_row_data[int, "Run"]
    cycle_number = first_row_data[int, "Cycle"]
    channel = first_row_data[int, "Channel"]

    run_table = run_metadata.run_table
    device_control_document = []
    for flow_cell, flow_cell_data in channel_data.groupby("Flow cell"):
        run_data = run_table[
            (run_table["Flow cell"].astype(str) == str(flow_cell))
            & (run_table["Channel"] == channel)
        ]
        run_info = SeriesData() if run_data.empty else df_to_series_data(run_data)
        # All the info needed in the device control document is the same for all flow cell data
        flow_cell_info = SeriesData(flow_cell_data.iloc[0])
        device_control_document.append(
            DeviceControlDocument(
                device_type=constants.DEVICE_TYPE,
                flow_cell_identifier=str(flow_cell),
                sample_temperature_setting=flow_cell_info.get(
                    float, "Temperature (°C)"
                ),
                device_control_custom_info={
                    "Analyte 1 Contact time": quantity_or_none(
                        TQuantityValueSecondTime,
                        flow_cell_info.get(float, "Analyte 1 Contact time (s)"),
                    ),
                    "Analyte 1 Dissociation time": quantity_or_none(
                        TQuantityValueSecondTime,
                        flow_cell_info.get(float, "Analyte 1 Dissociation time (s)"),
                    ),
                    "Analyte 1 Flow rate": quantity_or_none(
                        TQuantityValueMicroliterPerMinute,
                        flow_cell_info.get(float, "Analyte 1 Flow rate (µl/min)"),
                    ),
                    "Regeneration 1 Contact time": quantity_or_none(
                        TQuantityValueSecondTime,
                        flow_cell_info.get(float, "Regeneration 1 Contact time (s)"),
                    ),
                    "Regeneration 1 Flow rate": quantity_or_none(
                        TQuantityValueMicroliterPerMinute,
                        flow_cell_info.get(float, "Regeneration 1 Flow rate (µl/min)"),
                    ),
                    "Included": run_info.get(str, "Included"),
                    # TODO: replace with flow_cell_info an test!
                    "Sensorgram type": first_row_data.get(
                        str, "Sensorgram type", run_info.get(str, "Sensorgram type")
                    ),
                    "Level": quantity_or_none(
                        TQuantityValueResonanceUnits, run_info.get(float, "Level (RU)")
                    ),
                },
            )
        )

    capture_solution = _first_not_null_or_none(channel_data["Capture 1 Solution"])
    analyte_solution = first_row_data.get(str, "Analyte 1 Solution")
    kinetics_data = (
        evaluation_kinetics.get_data(channel, capture_solution, analyte_solution)
        if capture_solution and analyte_solution
        else None
    )
    data_processing_document = dict(metadata.data_processing_document or {})
    data_processing_document.update(
        {
            "Acceptance State": kinetics_data.acceptance_state,
            "Curve Markers": kinetics_data.curve_markers,
            "Kinetics Model": kinetics_data.kinetics_model,
        }
        if kinetics_data is not None
        else {}
    )

    return Measurement(
        identifier=random_uuid_str(),
        sample_identifier=f"Run{run}_Cycle{cycle_number}_Channel{channel}",
        type_=MeasurementType.SURFACE_PLASMON_RESONANCE,
        method_name=run_metadata.method_name,
        ligand_identifier=run_info.get(str, "Ligand"),
        device_control_document=device_control_document,
        sample_custom_info={
            "Run": run,
            "Cycle": cycle_number,
            "Channel": channel,
            "Analyte 1 Solution": analyte_solution,
            "Analyte 1 Plate id": first_row_data.get(str, "Analyte 1 Plate id"),
            "Analyte 1 Position": first_row_data.get(str, "Analyte 1 Position"),
            "Analyte 1 Control type": first_row_data.get(str, "Analyte 1 Control type"),
            "Regeneration 1 Solution": first_row_data.get(
                str, "Regeneration 1 Solution"
            ),
            "Regeneration 1 Plate id": first_row_data.get(
                str, "Regeneration 1 Plate id"
            ),
            "Regeneration 1 Position": first_row_data.get(
                str, "Regeneration 1 Position"
            ),
            "Regeneration 1 Control type": first_row_data.get(
                str, "Regeneration 1 Control type"
            ),
            # Capture data is not reported for the Reference flow cell,
            # so we have to look for the first non-null value
            "Capture 1 Solution": capture_solution,
            "Capture 1 Plate id": _first_not_null_or_none(
                channel_data["Capture 1 Plate id"]
            ),
            "Capture 1 Position": _first_not_null_or_none(
                channel_data["Capture 1 Position"]
            ),
            "Capture 1 Control type": _first_not_null_or_none(
                channel_data["Capture 1 Control type"]
            ),
            "Analyte 1 Concentration": quantity_or_none(
                TQuantityValueNanomolar,
                first_row_data.get(float, "Analyte 1 Concentration (nM)"),
            ),
            "Analyte 1 Molecular weight": quantity_or_none(
                TQuantityValueDalton,
                first_row_data.get(float, "Analyte 1 Molecular weight (Da)"),
            ),
        },
        binding_on_rate_measurement_datum__kon_=(
            kinetics_data.binding_on_rate_measurement_datum
            if kinetics_data is not None
            else None
        ),
        binding_off_rate_measurement_datum__koff_=(
            kinetics_data.binding_off_rate_measurement_datum
            if kinetics_data is not None
            else None
        ),
        equilibrium_dissociation_constant__kd_=(
            kinetics_data.equilibrium_dissociation_constant
            if kinetics_data is not None
            else None
        ),
        maximum_binding_capacity__rmax_=(
            kinetics_data.maximum_binding_capacity
            if kinetics_data is not None
            else None
        ),
        processed_data_custom_info=(
            {
                "Kinetics Chi squared": quantity_or_none(
                    TQuantityValueSquareResonanceUnits,
                    kinetics_data.kinetics_chi_squared,
                ),
                "tc": quantity_or_none(TQuantityValueUnitless, kinetics_data.tc),
            }
            if kinetics_data is not None
            else None
        ),
        report_point_data=map_rows(channel_data, _get_report_point),
        data_processing_document=data_processing_document,
    )


def _get_report_point(row: SeriesData) -> ReportPoint:
    """Extract report point data from the channel data."""
    return ReportPoint(
        identifier=f"Run{row[int, 'Run']}_Channel{row[int, 'Channel']}_Cycle{row[int, 'Cycle']}_FlowCell{row[str, 'Flow cell']}_Name{row[str, 'Name']}",
        identifier_role=row[str, "Name"],
        absolute_resonance=row[float, "Absolute response (RU)"],
        time_setting=row[float, "Time (s)"],
        relative_resonance=row.get(float, "Relative response (RU)"),
        custom_info={
            "Step name": row.get(str, "Name"),
            "Step purpose": row.get(str, "Step purpose"),
            "Window": quantity_or_none(
                TQuantityValueSecondTime, row.get(float, "Window (s)")
            ),
            "Baseline": row.get(str, "Baseline"),
        },
    )


def _first_not_null_or_none(series: pd.Series[Any]) -> str | None:
    """Get the first non-null value from a Series or None."""
    return str(series[idx]) if (idx := series.first_valid_index()) is not None else None
