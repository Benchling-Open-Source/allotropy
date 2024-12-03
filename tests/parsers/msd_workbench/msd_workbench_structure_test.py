import pandas as pd

from allotropy.parsers.constants import DEFAULT_EPOCH_TIMESTAMP, NOT_APPLICABLE
from allotropy.parsers.msd_workbench.constants import SOFTWARE_NAME
from allotropy.parsers.msd_workbench.msd_workbench_structure import (
    create_measurement_groups,
    create_metadata,
    PlateData,
)


def test_create_metadata() -> None:
    file_name = "Z:\\MSD-WP\\Export\\22M0TALA85_2023-09-08-133933.txt"
    metadata = create_metadata(file_name)
    assert metadata.file_name == file_name.rsplit("\\", 1)[-1]
    assert metadata.unc_path == file_name
    assert metadata.software_name == SOFTWARE_NAME
    assert metadata.model_number == NOT_APPLICABLE
    assert (
        metadata.asm_file_identifier
        == "Z:\\MSD-WP\\Export\\22M0TALA85_2023-09-08-133933.json"
    )
    assert metadata.data_system_instance_id == NOT_APPLICABLE


def test_create_measurement_groups() -> None:
    columns = [
        "Sample",
        "Assay",
        "Well",
        "Spot",
        "Signal",
        "Concentration",
        "Detection Range",
        "Dilution Factor",
    ]
    data = pd.DataFrame(
        [
            [
                "S001",
                "SARS-CoV-2 Nucleocapsid",
                "A02",
                3,
                93,
                20.0,
                "Above Detection Range",
                1,
            ],
            [
                "S002",
                "SARS-CoV-2 Nucleocapsid",
                "A03",
                4,
                85,
                15.0,
                "Within Detection Range",
                2,
            ],
        ]
    )
    data.columns = pd.Index(columns)
    plate_data = PlateData.create(data, "Plate_2BO40AW287")
    measurement_groups = create_measurement_groups(plate_data)
    assert len(measurement_groups) == 2
    for group in measurement_groups:
        assert group.measurement_time == DEFAULT_EPOCH_TIMESTAMP
        assert len(group.measurements) == 1
        for measurement in group.measurements:
            assert measurement.luminescence in [93, 85]
            assert measurement.location_identifier in ["A02", "A03"]
            assert measurement.well_location_identifier in ["3", "4"]
            assert measurement.sample_identifier in ["S001_A02", "S002_A03"]
            assert measurement.mass_concentration in [20, 15]
            assert measurement.measurement_custom_info is not None
            assert measurement.measurement_custom_info["detection range"] in [
                "Above Detection Range",
                "Within Detection Range",
            ]
            assert (
                measurement.measurement_custom_info["assay identifier"]
                == "SARS-CoV-2 Nucleocapsid"
            )
