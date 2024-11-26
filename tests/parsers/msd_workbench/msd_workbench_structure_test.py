from _pytest.python_api import raises
import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import DEFAULT_EPOCH_TIMESTAMP, NOT_APPLICABLE
from allotropy.parsers.msd_workbench.msd_workbench_structure import (
    create_measurement_groups,
    create_metadata,
    Header,
    PlateData,
)


def test_create_metadata() -> None:
    file_name = "Z:\\MSD-WP\\Export\\22M0TALA85_2023-09-08-133933.txt"
    header = Header.create(file_name)
    metadata = create_metadata(Header.create(file_name))
    assert metadata.file_name == file_name.rsplit("\\", 1)[-1]
    assert metadata.unc_path == file_name
    assert metadata.software_name == header.name
    assert metadata.model_number == header.model
    assert (
        metadata.asm_file_identifier
        == "Z:\\MSD-WP\\Export\\22M0TALA85_2023-09-08-133933.json"
    )
    assert metadata.data_system_instance_id == NOT_APPLICABLE


def test_create_well_data() -> None:
    data = pd.DataFrame(
        [
            ["Plate_2BO40AW287", None],
            [
                "Sample",
                "Assay",
                "Well",
                "Spot",
                "Signal",
                "Concentration",
                "Detection Range",
                "Dilution Factor",
            ],
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
    plate_data = PlateData.create(data)
    assert plate_data.measurement_time == DEFAULT_EPOCH_TIMESTAMP
    assert plate_data.plate_well_count == 2
    assert plate_data.well_plate_id == "2BO40AW287"
    assert len(plate_data.well_data) == 2
    for well in plate_data.well_data:
        assert well.luminescence in [93, 85]
        assert well.location_identifier in ["A02_3", "A03_4"]
        assert well.sample_identifier in ["S001_A02", "S002_A03"]
        assert well.mass_concentration in [20, 15]
        assert well.measurement_custom_info is not None
        assert well.measurement_custom_info["detection range"] in [
            "Above Detection Range",
            "Within Detection Range",
        ]
        assert (
            well.measurement_custom_info["assay identifier"]
            == "SARS-CoV-2 Nucleocapsid"
        )
        assert well.dilution_factor in [1, 2]


def test_create_well_data_without_plate_id_fails() -> None:
    data = pd.DataFrame(
        [
            [
                "Sample",
                "Assay",
                "Well",
                "Spot",
                "Signal",
                "Concentration",
                "Detection Range",
                "Dilution Factor",
            ],
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
    msg = "Plate ID not found in the first row of the data"
    with raises(AllotropeConversionError, match=msg):
        PlateData.create(data)


def test_create_measurement_groups() -> None:
    data = pd.DataFrame(
        [
            ["Plate_2BO40AW287", None],
            [
                "Sample",
                "Assay",
                "Well",
                "Spot",
                "Signal",
                "Concentration",
                "Detection Range",
                "Dilution Factor",
            ],
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
    plate_data = PlateData.create(data)
    measurement_groups = create_measurement_groups(plate_data)
    assert len(measurement_groups) == 2
    for group in measurement_groups:
        assert group.measurement_time == DEFAULT_EPOCH_TIMESTAMP
        assert len(group.measurements) == 1
        for measurement in group.measurements:
            assert measurement.luminescence in [93, 85]
            assert measurement.location_identifier in ["A02_3", "A03_4"]
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
