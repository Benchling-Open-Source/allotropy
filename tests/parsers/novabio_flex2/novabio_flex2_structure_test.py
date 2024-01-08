import re
from typing import Optional

import pandas as pd
import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.novabio_flex2.constants import (
    MOLAR_CONCENTRATION_CLS_BY_UNIT,
    PROPERTY_MAPPINGS,
)
from allotropy.parsers.novabio_flex2.novabio_flex2_structure import (
    Analyte,
    Data,
    Sample,
    SampleList,
    Title,
)
from tests.parsers.novabio_flex2.novabio_flex2_data import (
    get_data,
    get_input_stream,
    get_input_title,
)


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
@pytest.mark.short
def test_create_title(
    filename: str, processing_time: str, device_identifier: Optional[str]
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
@pytest.mark.short
def test_create_title_invalid_filename(filename: str) -> None:
    expected_regex_raw = f"{filename} is not valid. File name is expected to have format of SampleResultsYYYY-MM-DD_HHMMSS.csv or SampleResults<Analyzer ID>YYYY-MM-DD_HHMMSS.csv where <Analyzer ID> is defined in Settings"
    expected_regex = re.escape(expected_regex_raw)
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        Title.create(filename)


@pytest.mark.short
def test_create_analyte() -> None:
    nh4_analyte = Analyte.create("NH4+", 100)
    assert nh4_analyte.name == "ammonium"
    assert nh4_analyte.molar_concentration == MOLAR_CONCENTRATION_CLS_BY_UNIT["mmol/L"](
        value=100
    )

    gluc_analyte = Analyte.create("Gluc", 1.1)
    assert gluc_analyte.name == "glucose"
    assert gluc_analyte.molar_concentration == MOLAR_CONCENTRATION_CLS_BY_UNIT["g/L"](
        value=1.1
    )


@pytest.mark.short
def test_create_invalid_analyte() -> None:
    expected_regex_raw = "Unrecognized analyte name: 'FAKE'. Only ['Ca++', 'Gln', 'Glu', 'Gluc', 'HCO3', 'K+', 'Lac', 'NH4+', 'Na+'] are supported."
    expected_regex = re.escape(expected_regex_raw)
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        Analyte.create("FAKE", 100)


@pytest.mark.short
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
    sample = Sample.create(pd.Series(data=data))

    assert sample.identifier == "BP_R10_KP_008_D0"
    assert sample.role_type == "Spent Media"
    assert sample.measurement_time == "2022-06-24T14:34:52"
    assert sample.batch_identifier == "KP_008"
    assert sorted(sample.analytes) == sorted(
        [
            Analyte.create("Gln", 1.83),
            Analyte.create("Ca++", 0.82),
        ]
    )
    assert sample.properties == {
        "co2_saturation": PROPERTY_MAPPINGS["co2_saturation"]["cls"](value=0),
        "o2_saturation": PROPERTY_MAPPINGS["o2_saturation"]["cls"](value=100.0),
    }


@pytest.mark.short
def test_sample_sorting() -> None:
    analytes = [
        Analyte.create("Gln", 1.83),
        Analyte.create("Glu", 0.33),
        Analyte.create("Gluc", 2.65),
        Analyte.create("Lac", 0.18),
        Analyte.create("NH4+", 0.48),
    ]
    assert sorted(analytes) == [
        Analyte.create("NH4+", 0.48),
        Analyte.create("Gluc", 2.65),
        Analyte.create("Glu", 0.33),
        Analyte.create("Gln", 1.83),
        Analyte.create("Lac", 0.18),
    ]


@pytest.mark.short
def test_create_sample_list() -> None:
    sample_list = SampleList.create(
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

    assert sample_list.analyst == "Kermit"
    assert len(sample_list.samples) == 2
    assert sample_list.samples[0].identifier == "SAMPLE_1"
    assert sample_list.samples[1].identifier == "SAMPLE_2"


@pytest.mark.short
def test_create_sample_list_invalid_no_samples() -> None:
    df = pd.DataFrame()
    with pytest.raises(AllotropeConversionError, match="Unable to find any sample."):
        SampleList.create(df)


@pytest.mark.short
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
        SampleList.create(df)


@pytest.mark.short
def test_create_data() -> None:
    named_file_contents = NamedFileContents(get_input_stream(), get_input_title())
    assert Data.create(named_file_contents) == get_data()
