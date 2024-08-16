from __future__ import annotations

from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Data,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.roche_cedex_hires import constants
from allotropy.parsers.roche_cedex_hires.roche_cedex_hires_reader import (
    RocheCedexHiResReader,
)
from allotropy.parsers.utils.pandas import df_to_series_data, map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def _create_metadata(data: SeriesData, file_name: str) -> Metadata:
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


def _create_measurement_groups(data: SeriesData) -> MeasurementGroup:
    # Cell counts are measured in cells/mL, but reported in millions of cells/mL
    viable_cell_density = data[float, "Viable Cell Conc."] / 1e6
    total_cell_density = data.get(float, "Total Cell Conc.")
    if total_cell_density:
        total_cell_density /= 1e6
    dead_cell_density = data.get(float, "Dead Cell Conc.")
    if dead_cell_density:
        dead_cell_density /= 1e6

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
                total_cell_density=total_cell_density,
                dead_cell_count=data.get(float, "Dead Cell Count"),
                dead_cell_density=dead_cell_density,
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


def create_data(named_file_contents: NamedFileContents) -> Data:
    df = RocheCedexHiResReader.read(named_file_contents)
    return Data(
        _create_metadata(
            df_to_series_data(df.head(1), "Unable to parse first row in dataset."),
            named_file_contents.original_file_name,
        ),
        map_rows(df, _create_measurement_groups),
    )
