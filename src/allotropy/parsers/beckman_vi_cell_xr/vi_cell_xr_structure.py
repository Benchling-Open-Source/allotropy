from __future__ import annotations

import re

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Data,
    MeasurementRow,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.beckman_vi_cell_xr.constants import (
    DEFAULT_ANALYST,
    DEFAULT_VERSION,
    MODEL_NUMBER,
    MODEL_RE,
    SOFTWARE_NAME,
    XrVersion,
)
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_reader import ViCellXRReader
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_txt_reader import ViCellXRTXTReader
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_from_series,
    try_float_from_series_or_none,
    try_str_from_series,
    try_str_from_series_or_none,
)


def create_row(data: pd.Series[str]) -> MeasurementRow:
    timestamp = assert_not_none(
        try_str_from_series_or_none(data, "Sample date/time")
        or try_str_from_series_or_none(data, "Sample date")
    )
    total_cell_count = try_float_from_series_or_none(data, "Total cells")
    total_cell_count = (
        total_cell_count if total_cell_count is None else round(total_cell_count)
    )
    viable_cell_count = try_float_from_series_or_none(data, "Viable cells")
    viable_cell_count = (
        viable_cell_count if viable_cell_count is None else round(viable_cell_count)
    )

    return MeasurementRow(
        measurement_identifier=random_uuid_str(),
        timestamp=timestamp,
        sample_identifier=try_str_from_series(data, "Sample ID"),
        cell_type_processing_method=try_str_from_series_or_none(data, "Cell type"),
        cell_density_dilution_factor=try_float_from_series_or_none(
            data, "Dilution factor"
        ),
        viability=try_float_from_series(data, "Viability (%)"),
        viable_cell_density=try_float_from_series(data, "Viable cells/ml (x10^6)"),
        total_cell_count=total_cell_count,
        total_cell_density=try_float_from_series_or_none(
            data, "Total cells/ml (x10^6)"
        ),
        average_total_cell_diameter=try_float_from_series_or_none(
            data, "Avg. diam. (microns)"
        ),
        viable_cell_count=viable_cell_count,
        average_total_cell_circularity=try_float_from_series_or_none(
            data, "Avg. circ."
        ),
        analyst=DEFAULT_ANALYST,
    )


def create_rows(data: pd.DataFrame) -> list[MeasurementRow]:
    return list(
        data.apply(create_row, axis="columns")  # type:ignore[call-overload]
    )


def create_data(reader: ViCellXRTXTReader | ViCellXRReader) -> Data:
    serial_number_str = try_str_from_series(reader.file_info, "serial")
    try:
        serial_number = serial_number_str[serial_number_str.rindex(":") + 1 :].strip()
    except ValueError:
        serial_number = None

    match = re.match(
        MODEL_RE,
        try_str_from_series(reader.file_info, "model"),
        flags=re.IGNORECASE,
    )
    try:
        version_str = assert_not_none(match).groupdict()["version"]
        version_str = ".".join(version_str.split(".")[0:2])
        version = XrVersion(version_str)
    except (AttributeError, AllotropeConversionError):
        version = DEFAULT_VERSION
    except ValueError as e:
        msg = f"Invalid Beckman VI-Cell XR version: {version_str}"
        raise AllotropeConversionError(msg) from e

    metadata = Metadata(
        device_type="brightfield imager (cell counter)",
        detection_type="brightfield",
        model_number=MODEL_NUMBER,
        equipment_serial_number=serial_number,
        software_name=SOFTWARE_NAME,
        software_version=version.value,
    )

    return Data(metadata, create_rows(reader.data))
