from pathlib import Path

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.liquid_handler.benchling._2024._11.liquid_handler import (
    Error,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.beckman_echo_plate_reformat import constants
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(header_footer_data: SeriesData, file_path: str) -> Metadata:
    path = Path(file_path)
    return Metadata(
        file_name=path.name,
        asm_file_identifier=path.with_suffix(".json").name,
        unc_path=str(path),
        data_system_instance_identifier=NOT_APPLICABLE,
        device_type=constants.DEVICE_TYPE,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        software_version=header_footer_data[str, "Instrument Software Version"],
        # description=header_footer_data[str, "Instrument Model"],
        # identifier=header_footer_data[str, "Run ID"],
        equipment_serial_number=header_footer_data[str, "Instrument Serial Number"],
        software_name=header_footer_data[str, "Application Name"],
    )


def _create_measurement(row_data: SeriesData) -> Measurement:
    def convert_echo_nl_to_ul(value: float | None) -> float:
        return (
            (value * constants.PLATE_REFORMAT_REPORT_VOLUME_CONVERSION_TO_UL)
            if value
            else None
        )

    return Measurement(
        identifier=random_uuid_str(),
        measurement_time=row_data[str, "Date Time Point"],
        sample_identifier=row_data.get(str, "Sample ID", NOT_APPLICABLE),
        source_plate=row_data[str, "Source Plate Barcode"],
        source_well=row_data[str, "Source Well"],
        source_location=row_data[str, "Source Plate Name"],
        destination_plate=row_data[str, "Destination Plate Barcode"],
        destination_well=row_data[str, "Destination Well"],
        destination_location=row_data[str, "Destination Plate Name"],
        aspiration_volume=convert_echo_nl_to_ul(row_data.get(float, "Actual Volume")),
        transfer_volume=convert_echo_nl_to_ul(row_data.get(float, "Actual Volume")),
        injection_volume_setting=convert_echo_nl_to_ul(
            row_data.get(float, "Transfer Volume")
        ),
        device_control_custom_info={
            "sample name": row_data.get(str, "Sample Name"),
            "survey fluid volume": convert_echo_nl_to_ul(
                row_data.get(float, "Survey Fluid Volume")
            ),
            "current fluid volume": convert_echo_nl_to_ul(
                row_data.get(float, "Current Fluid Volume")
            ),
            "intended transfer volume": convert_echo_nl_to_ul(
                row_data.get(float, "Transfer Volume")
            ),
            "source labware name": row_data.get(str, "Source Plate Type"),
            "destination labware name": row_data.get(str, "Destination Plate Type"),
            "fluid composition": row_data.get(str, "Fluid Composition"),
            "fluid units": row_data.get(str, "Fluid Units"),
            "fluid type": row_data.get(str, "Fluid Type"),
            "transfer status": row_data.get(str, "Transfer Status", NOT_APPLICABLE),
        },
        errors=[
            Error(
                error=row_data[str, "Transfer Status"],
                feature=row_data[str, "Transfer Status"].split(": ")[0],
            )
        ]
        if row_data.get(str, "Transfer Status")
        else [],
    )


def create_measurement_groups(
    data: pd.DataFrame, header: SeriesData
) -> list[MeasurementGroup]:

    return [
        MeasurementGroup(
            analyst=header[str, "User Name"],
            analytical_method_identifier=header.get(str, "Protocol Name"),
            measurements=map_rows(data, _create_measurement),
        )
    ]
