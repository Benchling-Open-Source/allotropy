from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.liquid_handler.benchling._2024._11.liquid_handler import (
    Device,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.beckman_coulter_biomek import constants
from allotropy.parsers.beckman_coulter_biomek.constants import FileFormat
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(data: SeriesData, file_path: str) -> Metadata:
    pod_head_serial_columns = [
        str(column) for column in data.series.index if "head serial number" in column
    ]

    devices = []
    for pod_head_serial_column in pod_head_serial_columns:
        serial_value = data.get(str, pod_head_serial_column)
        # Skip if value is "None", empty, or whitespace only
        if (
            serial_value
            and serial_value.strip()
            and serial_value.strip().lower() != "none"
        ):
            devices.append(
                Device(
                    identifier=pod_head_serial_column.split(" ")[0],
                    device_type=constants.PROBE_HEAD_DEVICE_TYPE,
                    serial_number=serial_value,
                    product_manufacturer=constants.PRODUCT_MANUFACTURER,
                )
            )

    path = Path(file_path)
    return Metadata(
        file_name=path.name,
        asm_file_identifier=path.with_suffix(".json").name,
        unc_path=str(path),
        data_system_instance_identifier=NOT_APPLICABLE,
        device_type=constants.DEVICE_TYPE,
        equipment_serial_number=_get_non_empty_string(data, "Unit serial number"),
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        software_name=constants.SOFTWARE_NAME,
        devices=devices,
    )


def _get_non_empty_string(data: SeriesData, key: str) -> str | None:
    """Get string value from SeriesData, returning None for empty/whitespace strings."""
    value = data.get(str, key, validate=SeriesData.NOT_NAN)
    return value if value and value.strip() else None


def _get_sample_identifier(data: SeriesData, key: str) -> str:
    """Get sample identifier, returning NOT_APPLICABLE for empty/whitespace strings."""
    value = data.get(str, key, validate=SeriesData.NOT_NAN)
    return value if value and value.strip() else NOT_APPLICABLE


@dataclass(frozen=True)
class FieldMapping:
    """Configuration for mapping data fields to measurement fields."""

    # Required fields first
    time_field: str
    aspiration_volume_field: str
    transfer_volume_field: str

    # Optional fields with defaults
    sample_id_field: str | None = None
    sample_id_default: str = NOT_APPLICABLE

    # Source fields
    source_location_field: str | None = None
    source_well_field: str | None = None
    source_plate_field: str | None = None
    source_labware_name_field: str | None = None
    source_technique_field: str | None = None

    # Destination fields
    destination_location_field: str | None = None
    destination_well_field: str | None = None
    destination_plate_field: str | None = None
    destination_labware_name_field: str | None = None
    destination_technique_field: str | None = None

    # Device fields
    probe_field: str | None = None
    pod_field: str | None = None


class MeasurementStrategy(ABC):
    """Abstract strategy for creating measurements from different file formats."""

    @abstractmethod
    def create_measurements(self, data: pd.DataFrame) -> list[Measurement]:
        """Create measurements from DataFrame based on the specific file format."""
        pass


class UnifiedTransferStrategy(MeasurementStrategy):
    """Strategy for unified transfer format - single row per transfer."""

    def __init__(self) -> None:
        self.mapping = FieldMapping(
            time_field="Time Stamp",
            aspiration_volume_field="Amount",
            transfer_volume_field="Amount",
            sample_id_field="Destination Sample Name",
            source_location_field="Source Position",
            source_well_field="Source Well Index",
            source_plate_field="Source Labware Barcode",
            source_labware_name_field="Source Labware Name",
            destination_location_field="Destination Position",
            destination_well_field="Destination Well Index",
            destination_plate_field="Destination Labware Barcode",
            destination_labware_name_field="Destination Labware Name",
            probe_field="Probe",
            pod_field="Pod",
        )

    def create_measurements(self, data: pd.DataFrame) -> list[Measurement]:
        measurements: list[Measurement] = []

        def map_row(row_data: SeriesData) -> None:
            measurements.append(self._create_measurement_from_row(row_data))

        map_rows(data, map_row)
        return measurements

    def _create_measurement_from_row(self, row_data: SeriesData) -> Measurement:
        return _create_measurement_from_mapping(row_data, None, self.mapping)


class PairedTransferStrategy(MeasurementStrategy):
    """Base strategy for formats that pair aspirate/dispense steps."""

    def __init__(self, mapping: FieldMapping) -> None:
        self.mapping = mapping

    def create_measurements(self, data: pd.DataFrame) -> list[Measurement]:
        measurements: list[Measurement] = []
        aspirations: dict[str, SeriesData] = {}

        def map_row(row_data: SeriesData) -> None:
            transfer_step = row_data[str, "Transfer Step"]
            probe = row_data.get(str, "Probe", default="default")

            if transfer_step == constants.TransferStep.ASPIRATE.value:
                if probe in aspirations:
                    msg = f"Got a second Aspirate step before a Dispense step for probe {probe}"
                    raise AssertionError(msg)
                aspirations[probe] = deepcopy(row_data)
            elif transfer_step == constants.TransferStep.DISPENSE.value:
                if probe not in aspirations:
                    msg = (
                        f"Got a Dispense step before an Aspirate step for probe {probe}"
                    )
                    raise AssertionError(msg)
                aspiration_data = aspirations.pop(probe)
                measurements.append(
                    _create_measurement_from_mapping(
                        aspiration_data, row_data, self.mapping
                    )
                )
            else:
                msg = f"Got unexpected Transfer Step: {transfer_step}"
                raise AssertionError(msg)

        map_rows(data, map_row)
        return measurements


class UnifiedPipettingStrategy(PairedTransferStrategy):
    """Strategy for unified pipetting format."""

    def __init__(self) -> None:
        super().__init__(
            FieldMapping(
                time_field="Time Stamp",
                aspiration_volume_field="Amount",
                transfer_volume_field="Amount",
                source_location_field="Deck Position",
                source_well_field="Well Index",
                source_plate_field="Labware Barcode",
                source_labware_name_field="Labware Name",
                source_technique_field="Liquid Handling Technique",
                destination_location_field="Deck Position",
                destination_well_field="Well Index",
                destination_plate_field="Labware Barcode",
                destination_labware_name_field="Labware Name",
                destination_technique_field="Liquid Handling Technique",
                probe_field="Probe",
                pod_field="Pod",
            )
        )


class PipettingStrategy(MeasurementStrategy):
    """Strategy for pipetting format - uses FIFO matching since no probe identifiers."""

    def __init__(self) -> None:
        self.mapping = FieldMapping(
            time_field="Time Stamp",
            aspiration_volume_field="Amount",
            transfer_volume_field="Amount",
            source_location_field="Position",
            source_well_field="Well Index",
            source_plate_field="Labware Barcode",
            source_labware_name_field="Labware Name",
            source_technique_field="Liquid Handling Technique",
            destination_location_field="Position",
            destination_well_field="Well Index",
            destination_plate_field="Labware Barcode",
            destination_labware_name_field="Labware Name",
            destination_technique_field="Liquid Handling Technique",
            pod_field="Pod",
        )

    def create_measurements(self, data: pd.DataFrame) -> list[Measurement]:
        measurements: list[Measurement] = []
        aspirations: list[SeriesData] = []

        def map_row(row_data: SeriesData) -> None:
            transfer_step = row_data[str, "Transfer Step"]
            if transfer_step == constants.TransferStep.ASPIRATE.value:
                aspirations.append(deepcopy(row_data))
            elif transfer_step == constants.TransferStep.DISPENSE.value:
                if not aspirations:
                    msg = "Got a Dispense step before an Aspirate step"
                    raise AssertionError(msg)
                aspiration_data = aspirations.pop(0)  # FIFO matching
                measurements.append(
                    _create_measurement_from_mapping(
                        aspiration_data, row_data, self.mapping
                    )
                )
            else:
                msg = f"Got unexpected Transfer Step: {transfer_step}"
                raise AssertionError(msg)

        map_rows(data, map_row)
        return measurements


def _create_measurement_from_mapping(
    source_data: SeriesData, dest_data: SeriesData | None, mapping: FieldMapping
) -> Measurement:
    """Create a measurement using field mapping configuration."""
    # For unified transfer, source_data contains all info, dest_data is None
    # For paired formats, source_data is aspiration, dest_data is dispense

    time_data = dest_data if dest_data else source_data

    # Sample identifier
    sample_id = mapping.sample_id_default
    if mapping.sample_id_field:
        sample_id = _get_sample_identifier(time_data, mapping.sample_id_field)

    # Helper to get field from appropriate data source
    def get_source_field(field: str | None) -> str | None:
        return _get_non_empty_string(source_data, field) if field else None

    def get_dest_field(field: str | None) -> str | None:
        data = dest_data if dest_data else source_data
        return _get_non_empty_string(data, field) if field else None

    def get_source_value(field: str | None) -> str | None:
        return source_data.get(str, field) if field else None

    def get_dest_value(field: str | None) -> str | None:
        data = dest_data if dest_data else source_data
        return data.get(str, field) if field else None

    # Build custom info
    custom_info = {}

    # Probe info - only add if field exists and has a non-empty value
    if mapping.probe_field:
        probe_value = time_data.get(str, mapping.probe_field)
        if probe_value and probe_value.strip():
            custom_info["probe"] = probe_value

    # Pod info
    if mapping.pod_field:
        pod_value = get_source_value(mapping.pod_field)
        if pod_value is not None:
            custom_info["pod"] = pod_value

    # Labware names
    if mapping.source_labware_name_field:
        source_labware_value = get_source_value(mapping.source_labware_name_field)
        if source_labware_value is not None:
            custom_info["source labware name"] = source_labware_value
    if mapping.destination_labware_name_field:
        dest_labware_value = get_dest_value(mapping.destination_labware_name_field)
        if dest_labware_value is not None:
            custom_info["destination labware name"] = dest_labware_value

    # Techniques
    if mapping.source_technique_field:
        source_technique_value = get_source_value(mapping.source_technique_field)
        if source_technique_value is not None:
            custom_info["source liquid handling technique"] = source_technique_value
    if mapping.destination_technique_field:
        dest_technique_value = get_dest_value(mapping.destination_technique_field)
        if dest_technique_value is not None:
            custom_info["destination liquid handling technique"] = dest_technique_value

    return Measurement(
        identifier=random_uuid_str(),
        measurement_time=time_data[str, mapping.time_field],
        sample_identifier=sample_id,
        source_plate=get_source_field(mapping.source_plate_field),
        source_well=source_data.get(str, mapping.source_well_field)
        if mapping.source_well_field
        else None,
        source_location=source_data.get(str, mapping.source_location_field)
        if mapping.source_location_field
        else None,
        destination_plate=get_dest_field(mapping.destination_plate_field),
        destination_well=time_data.get(str, mapping.destination_well_field)
        if mapping.destination_well_field
        else None,
        destination_location=time_data.get(str, mapping.destination_location_field)
        if mapping.destination_location_field
        else None,
        aspiration_volume=source_data[float, mapping.aspiration_volume_field],
        transfer_volume=time_data[float, mapping.transfer_volume_field],
        device_control_custom_info=custom_info,
    )


def _get_measurement_strategy(file_format: FileFormat) -> MeasurementStrategy:
    """Factory function to get the appropriate measurement strategy."""
    if file_format == FileFormat.UNIFIED_TRANSFER:
        return UnifiedTransferStrategy()
    elif file_format == FileFormat.PIPETTING:
        return PipettingStrategy()
    else:
        return UnifiedPipettingStrategy()


def create_measurement_groups(
    data: pd.DataFrame, header: SeriesData, file_format: FileFormat
) -> list[MeasurementGroup]:
    """Create measurement groups using the strategy pattern."""
    strategy = _get_measurement_strategy(file_format)
    measurements = strategy.create_measurements(data)

    return [
        MeasurementGroup(
            analyst=header[str, "Logged in user"],
            analytical_method_identifier=header.get(str, "Method"),
            measurements=measurements,
        )
    ]
