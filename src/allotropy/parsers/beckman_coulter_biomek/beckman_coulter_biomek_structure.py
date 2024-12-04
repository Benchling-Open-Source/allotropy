from copy import deepcopy
from pathlib import Path

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.liquid_handler.benchling._2024._11.liquid_handler import (
    Device,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.beckman_coulter_biomek import constants
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(data: SeriesData, file_path: str) -> Metadata:
    pod_head_serial_columns = [
        str(column) for column in data.series.index if "head serial number" in column
    ]
    devices = [
        Device(
            identifier=pod_head_serial_column.split(" ")[0],
            device_type=constants.PROBE_HEAD_DEVICE_TYPE,
            serial_number=data[str, pod_head_serial_column],
            product_manufacturer=constants.PRODUCT_MANUFACTURER,
        )
        for pod_head_serial_column in pod_head_serial_columns
        if data[str, pod_head_serial_column] != "None"
    ]

    path = Path(file_path)
    return Metadata(
        file_name=path.name,
        asm_file_identifier=path.with_suffix(".json").name,
        unc_path=str(path),
        data_system_instance_identifier=NOT_APPLICABLE,
        device_type=constants.DEVICE_TYPE,
        equipment_serial_number=data.get(str, "Unit serial number"),
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        software_name=constants.SOFTWARE_NAME,
        devices=devices,
    )


def _create_measurement(
    aspiration_data: SeriesData, dispense_data: SeriesData
) -> Measurement:
    return Measurement(
        identifier=random_uuid_str(),
        measurement_time=dispense_data[str, "Time Stamp"],
        sample_identifier=NOT_APPLICABLE,
        source_plate=aspiration_data[str, "Labware Barcode"],
        source_well=aspiration_data[str, "Well Index"],
        source_location=aspiration_data[str, "Deck Position"],
        destination_plate=dispense_data[str, "Labware Barcode"],
        destination_well=dispense_data[str, "Well Index"],
        destination_location=dispense_data[str, "Deck Position"],
        aspiration_volume=aspiration_data[float, "Amount"],
        transfer_volume=dispense_data[float, "Amount"],
        device_control_custom_info={
            "probe": dispense_data[str, "Probe"],
            "pod": aspiration_data.get(str, "Pod"),
            "source labware name": aspiration_data.get(str, "Labware Name"),
            "destination labware name": dispense_data.get(str, "Labware Name"),
            "source liquid handling technique": aspiration_data.get(
                str, "Liquid Handling Technique"
            ),
            "destination liquid handling technique": dispense_data.get(
                str, "Liquid Handling Technique"
            ),
        },
    )


def create_measurement_groups(
    data: pd.DataFrame, header: SeriesData
) -> list[MeasurementGroup]:
    # This function will be called for every row in the dataset, use it to create
    # a corresponding measurement group.
    measurements: list[Measurement] = []
    probe_to_aspiration: dict[str, SeriesData] = {}

    def map_to_measurements(row_data: SeriesData) -> None:
        probe = row_data[str, "Probe"]
        transfer_step = row_data[str, "Transfer Step"]
        if transfer_step == constants.TransferStep.ASPIRATE.value:
            if probe in probe_to_aspiration:
                msg = f"Got a second Aspirate step before a Transfer step for probe {probe}"
                raise AssertionError(msg)
            probe_to_aspiration[probe] = deepcopy(row_data)
        elif transfer_step == constants.TransferStep.DISPENSE.value:
            if probe not in probe_to_aspiration:
                msg = f"Got a Transfer step before an Aspirate step for probe {probe}"
                raise AssertionError(msg)
            aspiration_data = probe_to_aspiration.pop(probe)
            measurements.append(_create_measurement(aspiration_data, row_data))
        else:
            msg = f"Got unexpected Transfer Step: {transfer_step}"
            raise AssertionError(msg)

    map_rows(data, map_to_measurements)

    return [
        MeasurementGroup(
            analyst=header[str, "Logged in user"],
            analytical_method_identifier=header.get(str, "Method"),
            measurements=measurements,
        )
    ]
