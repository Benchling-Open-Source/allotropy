import re

import pandas as pd
import pytest

from allotropy.allotrope.schema_mappers.adm.solution_analyzer.benchling._2024._09.solution_analyzer import (
    Analyte,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.novabio_flex2.novabio_flex2_structure import (
    Sample,
    SampleData,
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
