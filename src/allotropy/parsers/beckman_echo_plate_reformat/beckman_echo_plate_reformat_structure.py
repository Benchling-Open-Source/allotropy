from functools import partial
from pathlib import Path

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.liquid_handler.benchling._2024._11.liquid_handler import (
    Error,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
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
        software_version=header_footer_data[str, "Application Version"],
        model_number=header_footer_data[str, "Instrument Model"],
        equipment_serial_number=header_footer_data[str, "Instrument Serial Number"],
        software_name=header_footer_data[str, "Application Name"],
        device_system_custom_info={
            "Instrument Software Version": header_footer_data.get(
                str, "Instrument Software Version"
            )
        },
        custom_info=header_footer_data.get_unread(),
    )


def _create_measurement(row_data: SeriesData, run_date_time: str | None) -> Measurement:
    def convert_echo_nl_to_ul(value: float | None) -> float | None:
        return (
            (value * constants.PLATE_REFORMAT_REPORT_VOLUME_CONVERSION_TO_UL)
            if value is not None
            else None
        )

    # If the Date Time Point only contains time (no date) combine with Run Date/Time to create measurement time.
    # We detect if there is a date in the timestamp by checking for a space, and if there is no space, add the date
    # component of
    date_time_point = row_data[str, "Date Time Point"]
    if " " not in date_time_point.strip():
        if not run_date_time or " " not in run_date_time:
            msg = "Cannot parse timestamp for measurement, 'Date Time Point' does not contain a date (time only) and there is no valid 'Run Date/Time' in the header to infer date from."
            raise AllotropeConversionError(msg)
        run_date_time_date = run_date_time.split(" ")
        date_time_point = f"{run_date_time_date[0]} {date_time_point}"

    return Measurement(
        identifier=random_uuid_str(),
        measurement_time=date_time_point,
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
            "survey fluid volume": row_data.get(
                float, "Survey Fluid Volume"
            ),  # This is already in uL, so don't convert to nL
            "current fluid volume": row_data.get(
                float, "Current Fluid Volume"
            ),  # This is already in uL, so don't convert to nL
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
        custom_info=row_data.get_unread(),
    )


def create_measurement_groups(
    data: pd.DataFrame, header: SeriesData
) -> list[MeasurementGroup]:
    run_date_time = header.get(str, "Run Date/Time")
    create_measurement = partial(_create_measurement, run_date_time=run_date_time)
    return [
        MeasurementGroup(
            analyst=header[str, "User Name"],
            analytical_method_identifier=header.get(str, "Protocol Name"),
            experimental_data_identifier=header.get(str, "Run ID"),
            measurements=map_rows(data, create_measurement),
            custom_info={
                "Run Date/Time": run_date_time,
            },
        )
    ]
