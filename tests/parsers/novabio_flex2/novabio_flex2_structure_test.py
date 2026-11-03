import re
from typing import Any

import pandas as pd
import pytest

from allotropy.allotrope.schema_mappers.adm.solution_analyzer.benchling._2024._09.solution_analyzer import (
    Analyte,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.novabio_flex2.constants import (
    DETECTION_PROPERTY_MAPPING,
    MEASURED_PROPERTIES_BY_DETECTION_TYPE,
)
from allotropy.parsers.novabio_flex2.novabio_flex2_structure import (
    create_measurement_groups,
    Sample,
    SampleData,
    SampleList,
    Title,
)
from allotropy.parsers.utils.pandas import SeriesData


@pytest.mark.parametrize(
    "filename,processing_time,device_identifier",
    [
        ("SampleResults2022-06-28_142558.csv", "2022-06-28 142558", None),
        (
            "SampleResultsT26918070C2021-02-18_104838.csv",
            "2021-02-18 104838",
            "T26918070C",
        ),
    ],
)
def test_create_title(
    filename: str, processing_time: str, device_identifier: str | None
) -> None:
    title = Title.create(filename)
    assert title.processing_time == processing_time
    assert title.device_identifier == device_identifier


@pytest.mark.parametrize(
    "filename",
    (
        "invalid_filename",  # no extension
        "T26918070C2021-02-18_104838.csv",  # filename does not start with SampleResults
        "SampleResults2021-02-18_104838T26918070C.csv",  # wrong order of timestamp and identifier
    ),
)
def test_create_title_invalid_filename(filename: str) -> None:
    expected_regex_raw = f"{filename} is not valid. File name is expected to have format of SampleResultsYYYY-MM-DD_HHMMSS.csv or SampleResults<Analyzer ID>YYYY-MM-DD_HHMMSS.csv where <Analyzer ID> is defined in Settings"
    expected_regex = re.escape(expected_regex_raw)
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        Title.create(filename)


def test_create_sample() -> None:
    data = {
        "Sample ID": "BP_R10_KP_008_D0",
        "Sample Type": "Spent Media",
        "Date & Time": pd.Timestamp("2022-06-24 14:34:52"),
        "Batch ID": "KP_008",
        "Operator": "Kermit",
        "Gln": 1.83,
        "Ca++": 0.82,
        "O2 Saturation": 100.0,
        "CO2 Saturation": 0,  # zero here makes sure we allow falsey values
        "Unmapped column": 5,
    }
    sample = Sample.create(SeriesData(), SeriesData(pd.Series(data=data)))

    assert sample.identifier == "BP_R10_KP_008_D0"
    assert sample.sample_type == "Spent Media"
    assert sample.measurement_time == "2022-06-24 14:34:52"
    assert sample.batch_identifier == "KP_008"
    assert sorted(sample.analytes) == sorted(
        [
            Analyte("glutamine", 1.83, "mmol/L"),
            Analyte("calcium", 0.82, "mmol/L"),
        ]
    )
    assert sample.carbon_dioxide_saturation == 0
    assert sample.oxygen_saturation == 100.0


def _get_detection_types(**sample_properties: Any) -> list[str | None]:
    sample = Sample(
        identifier="SAMPLE_1",
        sample_type="Spent Media",
        measurement_time="2025-02-09 10:40:00",
        batch_identifier="BATCH_123",
        **{"analytes": [Analyte("glucose", 4.5, "g/L")], **sample_properties},
    )
    groups = create_measurement_groups(
        Title(processing_time="2025-02-09 104000", device_identifier=None),
        SampleList(analyst="Kermit", samples=[sample]),
    )
    return [measurement.detection_type for measurement in groups[0].measurements]


@pytest.mark.parametrize(
    "ph,temperature,expected_detection_types",
    [
        # The pH-detector schema requires a pH value, so a vessel temperature on its own
        # must not produce a pH measurement.
        (None, 37.0, ["metabolite-detection"]),
        (None, None, ["metabolite-detection"]),
        (7.4, 37.0, ["metabolite-detection", "ph-detection"]),
        (7.4, None, ["metabolite-detection", "ph-detection"]),
    ],
)
def test_ph_detection_requires_ph_value(
    ph: float | None,
    temperature: float | None,
    expected_detection_types: list[str],
) -> None:
    assert (
        _get_detection_types(ph=ph, temperature=temperature) == expected_detection_types
    )


@pytest.mark.parametrize(
    "sample_properties,expected_detection_types",
    [
        # Units come from the file's unit row and are set on every sample, so they must not
        # produce a measurement on their own.
        (
            {
                "total_cell_density_unit": "x10^6Cells/mL",
                "viable_cell_density_unit": "x10^6Cells/mL",
            },
            ["metabolite-detection"],
        ),
        ({"po2_unit": "mmHg", "pco2_unit": "mmHg"}, ["metabolite-detection"]),
        (
            {"cell_type_processing_method": "CHO", "cell_density_dilution_factor": 1.0},
            ["metabolite-detection"],
        ),
        ({"analytes": []}, []),
        (
            {
                "viability": 84.5,
                "viable_cell_density": 20.235,
                "viable_cell_density_unit": "x10^6Cells/mL",
                "cell_density_dilution_factor": 6.0,
            },
            ["metabolite-detection", "cell-counting"],
        ),
        (
            {"po2": 38.2, "po2_unit": "mmHg", "pco2": 42.0, "pco2_unit": "mmHg"},
            ["metabolite-detection", "blood-gas-detection"],
        ),
        ({"osmolality": 322.0}, ["metabolite-detection", "osmolality-detection"]),
    ],
)
def test_measurements_require_measured_value(
    sample_properties: dict[str, Any],
    expected_detection_types: list[str],
) -> None:
    assert _get_detection_types(**sample_properties) == expected_detection_types


@pytest.mark.parametrize("detection_type", DETECTION_PROPERTY_MAPPING)
def test_measured_properties_are_detection_properties(detection_type: str) -> None:
    assert set(MEASURED_PROPERTIES_BY_DETECTION_TYPE[detection_type]) <= set(
        DETECTION_PROPERTY_MAPPING[detection_type]
    )


def test_create_sample_list() -> None:
    sample_data = SampleData.create(
        pd.DataFrame(
            {
                "Sample ID": ["SAMPLE_1", "SAMPLE_2"],
                "Sample Type": ["Spent Media", "Spent Media"],
                "Date & Time": [
                    pd.Timestamp("2022-06-24 14:34:52"),
                    pd.Timestamp("2022-06-24 14:34:52"),
                ],
                "Operator": ["Kermit", "Other"],
            }
        )
    )

    assert sample_data.sample_list.analyst == "Kermit"
    assert len(sample_data.sample_list.samples) == 2
    assert sample_data.sample_list.samples[0].identifier == "SAMPLE_1"
    assert sample_data.sample_list.samples[1].identifier == "SAMPLE_2"


def test_create_sample_list_invalid_no_samples() -> None:
    df = pd.DataFrame()
    with pytest.raises(AllotropeConversionError, match="Unable to find any sample."):
        SampleData.create(df)


def test_create_sample_list_invalid_no_analyst() -> None:
    df = pd.DataFrame(
        {
            "Sample ID": ["SAMPLE_1", "SAMPLE_2"],
            "Sample Type": ["Spent Media", "Spent Media"],
            "Date & Time": [
                pd.Timestamp("2022-06-24 14:34:52"),
                pd.Timestamp("2022-06-24 14:34:52"),
            ],
        }
    )
    with pytest.raises(AllotropeConversionError, match="Unable to find the Operator."):
        SampleData.create(df)
