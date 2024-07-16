from __future__ import annotations

import re

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Data,
    Measurement,
    MeasurementGroup,
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
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none


def _create_measurement_group(series: pd.Series[str]) -> MeasurementGroup:
    data = SeriesData(series)
    total_cell_count = data.try_float_or_none("Total cells")
    total_cell_count = (
        total_cell_count if total_cell_count is None else round(total_cell_count)
    )
    viable_cell_count = data.try_float_or_none("Viable cells")
    viable_cell_count = (
        viable_cell_count if viable_cell_count is None else round(viable_cell_count)
    )

    return MeasurementGroup(
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                timestamp=data.try_str("Sample date"),
                sample_identifier=data.try_str("Sample ID"),
                cell_type_processing_method=data.try_str_or_none("Cell type"),
                cell_density_dilution_factor=data.try_float_or_none("Dilution factor"),
                viability=data.try_float("Viability (%)"),
                viable_cell_density=data.try_float("Viable cells/ml (x10^6)"),
                total_cell_count=total_cell_count,
                total_cell_density=data.try_float_or_none("Total cells/ml (x10^6)"),
                average_total_cell_diameter=data.try_float_or_none("Avg. diam. (microns)"),
                viable_cell_count=viable_cell_count,
                average_total_cell_circularity=data.try_float_or_none("Avg. circ."),
                analyst=DEFAULT_ANALYST,
            )
        ]
    )


def _create_measurement_groups(data: pd.DataFrame) -> list[MeasurementGroup]:
    return list(
        data.apply(
            _create_measurement_group, axis="columns"
        )  # type:ignore[call-overload]
    )


def create_data(reader: ViCellXRTXTReader | ViCellXRReader) -> Data:
    serial_number_str = reader.file_info.try_str("serial")
    try:
        serial_number = serial_number_str[serial_number_str.rindex(":") + 1 :].strip()
    except ValueError:
        serial_number = None

    match = re.match(
        MODEL_RE,
        reader.file_info.try_str("model"),
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

    return Data(metadata, _create_measurement_groups(reader.data))
