from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat, NaN
from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.chemometec_nc_view import constants
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_nan


def create_metadata(data: SeriesData, file_name: str) -> Metadata:
    return Metadata(
        file_name=file_name,
        software_name=constants.SOFTWARE_NAME,
        device_type=constants.DEVICE_TYPE,
        equipment_serial_number=data[str, "INSTRUMENT"].split(":")[-1].strip(),
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        detection_type=constants.DETECTION_TYPE,
        model_number=NOT_APPLICABLE,
        unc_path=NOT_APPLICABLE,
    )


def create_measurement_groups(data: SeriesData) -> MeasurementGroup:
    return MeasurementGroup(
        analyst=data[str, "OPERATOR"],
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                processed_data_identifier=random_uuid_str(),
                timestamp=_format_timestamp(data[str, "NAME"]),
                sample_identifier=data[str, "SAMPLE ID"],
                viability=data[float, "VIABILITY (%)"],
                total_cell_density=_format_number(data.get(str, "TOTAL (cells/ml)")),
                viable_cell_density=_format_number(data.get(str, "LIVE (cells/ml)")),
                dead_cell_density=_format_number(data.get(str, "DEAD (cells/ml)")),
                average_total_cell_diameter=_format_number(
                    data.get(str, "DIAMETER (μm)")
                ),
                cell_aggregation_percentage=_format_number(
                    data.get(str, "AGGREGATES (%)")
                ),
                debris_index=data.get(float, "DEBRIS INDEX"),
                cell_density_dilution_factor=data.get(float, "DILUTION FACTOR"),
            )
        ],
    )


def _format_number(unit: str | None) -> JsonFloat:
    if not unit:
        return NaN
    return try_float_or_nan("".join(unit.split()))


def _format_timestamp(timestamp: str) -> str:
    return timestamp.split("-")[0]
