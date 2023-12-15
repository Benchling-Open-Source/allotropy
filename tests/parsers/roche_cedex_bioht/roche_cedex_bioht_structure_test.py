import pandas as pd
import pytest

from allotropy.allotrope.models.shared.definitions.custom import (
    TNullableQuantityValueMilliOsmolesPerKilogram,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_structure import (
    Analyte,
    AnalyteList,
    Data,
    Sample,
    Title,
)
from tests.parsers.roche_cedex_bioht.roche_cedex_bioht_data import get_data, get_reader


@pytest.mark.parametrize(
    "processing_time,model_number,device_serial,analyst",
    [
        ("2021-06-01 13:04:06", "CEDEX BIO HT", 12345, "Analyst1"),
        ("2022-06-01 00:10:06", "CEDEX BIO HT", 99999, "Analyst2"),
        ("2023-06-01 24:35:25", "CEDEX BIO HT", 00000, "Analyst3"),
    ],
)
@pytest.mark.short
def test_create_title(
    processing_time: str, model_number: str, device_serial: int, analyst: str
) -> None:
    title_data = {
        "data processing time": processing_time,
        "model number": model_number,
        "device serial number": device_serial,
        "analyst": analyst,
    }
    title = Title.create(pd.Series(title_data))

    assert title.data_processing_time == processing_time
    assert title.analyst == analyst
    assert title.model_number == model_number
    assert title.device_serial_number == str(device_serial)


@pytest.mark.short
def test_create_title_with_no_analyst() -> None:
    title_data = pd.Series({"device serial number": 1234})
    with pytest.raises(AllotropeConversionError, match="Unable to obtain analyst."):
        Title.create(title_data)


@pytest.mark.short
def test_create_title_with_no_serial_number() -> None:
    title_data = pd.Series({"analyst": "dummy"})
    with pytest.raises(
        AllotropeConversionError,
        match="Unable to obtain device serial number.",
    ):
        Title.create(title_data)


@pytest.mark.short
def test_create_analyte() -> None:
    data = pd.Series(
        {
            "analyte name": "glutamine",
            "concentration value": 2.45,
            "concentration unit": "mmol/L",
        }
    )
    analyte = Analyte.create(data)
    assert analyte.name == "glutamine"
    assert analyte.concentration_value == 2.45
    assert analyte.unit == "mmol/L"


@pytest.mark.short
def test_create_analyte_with_no_unit() -> None:
    data = pd.Series(
        {
            "analyte name": "aspartate",
            "concentration value": 1.45,
        }
    )
    analyte = Analyte.create(data)
    assert analyte.name == "aspartate"
    assert analyte.concentration_value == 1.45
    assert analyte.unit is None


@pytest.mark.short
def test_create_analyte_list() -> None:
    data = pd.DataFrame(
        {
            "analyte name": ["lactate", "glutamine", "osmolality"],
            "concentration unit": ["g/L", "mmol/L", "mosm/kg"],
            "concentration value": [2.45, 4.35, 3.7448],
        }
    )
    analyte_list = AnalyteList.create(data)

    assert analyte_list.analytes == [
        Analyte("lactate", 2.45, "g/L"),
        Analyte("glutamine", 4.35, "mmol/L"),
        Analyte("osmolality", 3.7448, "mosm/kg"),
    ]
    assert analyte_list.non_aggregrable_dict == {
        "osmolality": [TNullableQuantityValueMilliOsmolesPerKilogram(3.7448)]
    }
    assert analyte_list.num_measurement_docs == 1


@pytest.mark.short
def test_create_analyte_list_more_than_one_mesurement_docs() -> None:
    data = pd.DataFrame(
        {
            "analyte name": ["lactate", "glutamine", "glutamine"],
            "concentration unit": ["g/L", "mmol/L", "mmol/L"],
            "concentration value": [2.45, 4.35, 3.45],
        },
    )
    analyte_list = AnalyteList.create(data)

    assert analyte_list.analytes == [
        Analyte("lactate", 2.45, "g/L"),
        Analyte("glutamine", 4.35, "mmol/L"),
        Analyte("glutamine", 3.45, "mmol/L"),
    ]
    assert analyte_list.num_measurement_docs == 2
    assert analyte_list.non_aggregrable_dict == {}


@pytest.mark.short
def test_create_sample() -> None:
    samples_data = pd.DataFrame(
        {
            "sample identifier": ["PPDTEST1", "PPDTEST1", "PPDTEST2"],
            "batch identifier": ["batch_id", "batch_id", ""],
            "analyte name": ["lactate", "glutamine", "glutamine"],
            "concentration unit": ["g/L", "mmol/L", "mmol/L"],
            "concentration value": [2.45, 4.35, 0.4],
            "sample role type": ["Sample", "Sample", "Sample"],
            "measurement time": [
                "2021-05-20 16:55:51",
                "2021-05-20 16:56:51",
                "2023-05-20 16:55:51",
            ],
        }
    )
    sample = Sample.create(
        name="PPDTEST1",
        batch="batch_id",
        samples_data=samples_data,
    )
    assert sample.name == "PPDTEST1"
    assert sample.batch == "batch_id"
    assert sample.role_type == "Sample"
    assert sample.measurement_time == "2021-05-20 16:56:51"
    assert len(sample.analyte_list.analytes) == 2


@pytest.mark.short
def test_create_data() -> None:
    assert Data.create(get_reader()) == get_data()
