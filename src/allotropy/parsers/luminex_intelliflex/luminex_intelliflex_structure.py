from pathlib import Path

from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._09.multi_analyte_profiling import (
    Calibration,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.luminex_intelliflex.constants import DEFAULT_SOFTWARE_NAME
from allotropy.parsers.luminex_intelliflex.luminex_intelliflex_reader import (
    LuminexIntelliflexReader,
)
from allotropy.parsers.luminex_xponent.constants import DEFAULT_DEVICE_TYPE
from allotropy.parsers.luminex_xponent.luminex_xponent_structure import (
    create_calibration,
    create_measurement_groups as xponent_create_measurement_groups,
    Data,
    Header,
    Measurement,
    MeasurementList,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.pandas import map_rows


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


def create_measurement_groups(
    measurements: list[Measurement], header: Header
) -> tuple[list[MeasurementGroup], list[CalculatedDocument] | None]:
    return xponent_create_measurement_groups(measurements, header)


def create_data_from_reader(reader: LuminexIntelliflexReader) -> Data:
    return Data(
        header=Header.create(
            reader.header_data, reader.minimum_assay_bead_count_setting
        ),
        calibrations=map_rows(reader.calibration_data, create_calibration),
        measurement_list=MeasurementList.create(reader.results_data),
    )
