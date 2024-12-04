import pandas as pd

from allotropy.parsers.msd_workbench.msd_workbench_calculated_data_mapping import (
    create_calculated_data_groups,
)
from allotropy.parsers.msd_workbench.msd_workbench_structure import (
    create_measurement_groups,
    PlateData,
)


def test_create_calculated_data() -> None:
    columns = [
        "Sample",
        "Assay",
        "Well",
        "Spot",
        "Fit Statistic: RSquared",
        "Detection Range",
        "Dilution",
        "Concentration",
        "Signal",
        "Adjusted Signal",
        "Mean",
        "Adj. Sig. Mean",
        "CV",
        "% Recovery",
        "% Recovery Mean",
        "Calc. Concentration",
        "Calc. Conc. Mean",
    ]
    data = pd.DataFrame(
        [
            [
                "S001",
                "Spike (FL.1.5.1)",
                "A02",
                2,
                0.99,
                "Above Detection Range",
                None,
                54.2,
                3513,
                3513,
                3421,
                3420.5,
                3.8,
                98.1,
                99.9,
                53.2,
                54.1,
            ],
        ]
    )
    data.columns = pd.Index(columns)
    plate_data = PlateData.create(data, "Plate_2BO40AW287")
    measurement_groups = create_measurement_groups(plate_data)
    measurements = [
        measurement
        for group in measurement_groups
        for measurement in group.measurements
    ]
    calculated_data = create_calculated_data_groups(data, measurements)
    assert len(calculated_data) == 9
    for calc_data in calculated_data:
        assert calc_data.value in [
            3513,
            3421,
            3420.5,
            0.99,
            3.8,
            98.1,
            99.9,
            53.2,
            54.1,
        ]
