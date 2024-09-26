from __future__ import annotations

from decimal import Decimal

from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.roche_cedex_hires import constants
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(data: SeriesData, file_name: str) -> Metadata:
    return Metadata(
        file_name=file_name,
        device_type=constants.DEVICE_TYPE,
        detection_type=constants.DETECTION_TYPE,
        model_number=constants.MODEL_NUMBER,
        software_name=constants.CEDEX_SOFTWARE,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        asset_management_identifier=data[str, "System name"],
        description=data[str, "System description"],
        device_identifier=data[str, "Cedex ID"],
        brand_name=constants.BRAND_NAME,
    )


def create_measurement_groups(data: SeriesData) -> MeasurementGroup:
    # Cell counts are measured in cells/mL, but reported in millions of cells/mL
    viable_cell_density = float(
        Decimal(data[str, "Viable Cell Conc."]) / Decimal("1000000")
    )
    total_cell_density_val = data.get(str, "Total Cell Conc.")
    if total_cell_density_val:
        total_cell_density = float(Decimal(total_cell_density_val) / Decimal("1000000"))
    dead_cell_density_val = data.get(str, "Dead Cell Conc.")
    if dead_cell_density_val:
        dead_cell_density = float(Decimal(dead_cell_density_val) / Decimal("1000000"))

    return MeasurementGroup(
        analyst=data.get(str, "Username"),
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                timestamp=data[str, "Date finished"],
                sample_identifier=data[str, "Sample identifier"],
                batch_identifier=data.get(str, "Reactor identifier"),
                group_identifier=data.get(str, "Data set name"),
                viability=data[float, "Viability"],
                viable_cell_count=data.get(float, "Viable Cell Count"),
                viable_cell_density=viable_cell_density,
                total_cell_count=data.get(float, "Total Cell Count"),
                total_cell_density=total_cell_density
                if total_cell_density_val
                else None,
                dead_cell_count=data.get(float, "Dead Cell Count"),
                dead_cell_density=dead_cell_density if dead_cell_density_val else None,
                cell_type_processing_method=data.get(str, "Cell type name"),
                cell_density_dilution_factor=data.get(float, "Dilution"),
                sample_volume_setting=data.get(float, "Sample volume"),
                average_live_cell_diameter=data.get(float, "Avg Diameter"),
                average_compactness=data.get(float, "Avg Compactness"),
                average_area=data.get(float, "Avg Area"),
                average_perimeter=data.get(float, "Avg Perimeter"),
                average_segment_area=data.get(float, "Avg Segm. Area"),
                total_object_count=data.get(float, "Total Object Count"),
                standard_deviation=data.get(float, "Std Dev."),
                aggregate_rate=data.get(float, "Aggregate Rate"),
                sample_draw_time=data.get(str, "Sample draw Time"),
            )
        ],
    )
