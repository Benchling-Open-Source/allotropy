from __future__ import annotations

import re

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
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_reader import ViCellData
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none


def _create_measurement_group(data: SeriesData) -> MeasurementGroup:
    total_cell_count = data.get(float, "Total cells")
    total_cell_count = (
        total_cell_count if total_cell_count is None else round(total_cell_count)
    )
    viable_cell_count = data.get(float, "Viable cells")
    viable_cell_count = (
        viable_cell_count if viable_cell_count is None else round(viable_cell_count)
    )

    return MeasurementGroup(
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                timestamp=data[str, "Sample date"],
                sample_identifier=data[str, "Sample ID"],
                cell_type_processing_method=data.get(str, "Cell type"),
                cell_density_dilution_factor=data.get(float, "Dilution factor"),
                viability=data[float, "Viability (%)"],
                viable_cell_density=data[float, "Viable cells/ml (x10^6)"],
                total_cell_count=total_cell_count,
                total_cell_density=data.get(float, "Total cells/ml (x10^6)"),
                average_total_cell_diameter=data.get(float, "Avg. diam. (microns)"),
                viable_cell_count=viable_cell_count,
                average_total_cell_circularity=data.get(float, "Avg. circ."),
                analyst=DEFAULT_ANALYST,
            )
        ]
    )


def create_data(reader_data: ViCellData, file_name: str) -> Data:
    serial_number_str = reader_data.file_info[str, "serial"]
    try:
        serial_number = serial_number_str[serial_number_str.rindex(":") + 1 :].strip()
    except ValueError:
        serial_number = None

    match = re.match(
        MODEL_RE,
        reader_data.file_info[str, "model"],
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
        file_name=file_name,
    )

    return Data(metadata, map_rows(reader_data.data, _create_measurement_group))
