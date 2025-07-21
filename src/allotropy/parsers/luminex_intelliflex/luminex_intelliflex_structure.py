from pathlib import Path

from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._09.multi_analyte_profiling import (
    Calibration,
    Metadata,
)
from allotropy.parsers.luminex_intelliflex.constants import DEFAULT_SOFTWARE_NAME
from allotropy.parsers.luminex_xponent.constants import DEFAULT_DEVICE_TYPE
from allotropy.parsers.luminex_xponent.luminex_xponent_structure import Header


def create_metadata(
    header: Header, calibrations: list[Calibration], file_path: str
) -> Metadata:
    path = Path(file_path)
    return Metadata(
        file_name=path.name,
        asm_file_identifier=path.with_suffix(".json").name,
        unc_path=file_path,
        equipment_serial_number=header.equipment_serial_number,
        model_number=header.model_number,
        calibrations=calibrations,
        data_system_instance_identifier=header.data_system_instance_identifier,
        software_name=DEFAULT_SOFTWARE_NAME,
        software_version=header.software_version,
        device_type=DEFAULT_DEVICE_TYPE,
    )
