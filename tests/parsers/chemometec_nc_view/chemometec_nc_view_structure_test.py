import pandas as pd

from allotropy.parsers.chemometec_nc_view import constants
from allotropy.parsers.chemometec_nc_view.chemometec_nc_view_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.pandas import df_to_series_data


def test_create_metadata() -> None:
    data = {
        "INSTRUMENT": "S/N: 9002029999999999",
    }
    df_data = pd.DataFrame(data, index=[0])
    file_path = "chemometec_nc_view_example.csv"
    metadata = create_metadata(df_to_series_data(df_data), file_path)
    assert metadata.file_name == file_path
    assert metadata.software_name == constants.SOFTWARE_NAME
    assert metadata.device_type == constants.DEVICE_TYPE
    assert metadata.equipment_serial_number == "9002029999999999"
    assert metadata.product_manufacturer == constants.PRODUCT_MANUFACTURER
    assert metadata.detection_type == constants.DETECTION_TYPE
    assert metadata.model_number == NOT_APPLICABLE
    assert metadata.unc_path == file_path


def test_create_measurement_groups() -> None:
    data = {
        "OPERATOR": "John Doe",
        "NAME": "2023-11-01",
        "SAMPLE ID": "1",
        "VIABILITY (%)": "90",
        "TOTAL (cells/ml)": "1000",
        "LIVE (cells/ml)": "900",
        "DEAD (cells/ml)": "100",
        "DIAMETER (μm)": "10",
        "AGGREGATES (%)": "5",
        "DEBRIS INDEX": "0.1",
        "DILUTION FACTOR": "1",
    }
    df_data = pd.DataFrame(data, index=[0])
    measurement_groups = create_measurement_groups(df_to_series_data(df_data))
    assert measurement_groups.analyst == "John Doe"
    assert len(measurement_groups.measurements) == 1
    measurement = measurement_groups.measurements[0]
    assert measurement.sample_identifier == "1"
    assert measurement.viability == 90
    assert measurement.total_cell_density == 0.001
    assert measurement.viable_cell_density == 0.0009
    assert measurement.dead_cell_density == 0.0001
    assert measurement.average_total_cell_diameter == 10
    assert measurement.cell_aggregation_percentage == 5
    assert measurement.debris_index == 0.1
    assert measurement.cell_density_dilution_factor == 1
