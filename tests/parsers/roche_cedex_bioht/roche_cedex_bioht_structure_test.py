import pandas as pd
import pytest

from allotropy.exceptions import AllotropeConversionError, AllotropyParserError
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_structure import (
    create_measurements,
    RawMeasurement,
    Sample,
    Title,
)
from allotropy.parsers.utils.pandas import SeriesData


@pytest.mark.parametrize(
    "processing_time,model_number,device_serial,analyst,software_version",
    [
        ("2021-06-01 13:04:06", "CEDEX BIO HT", 12345, "Analyst1", "1.0.0"),
        ("2022-06-01 00:10:06", "CEDEX BIO HT", 99999, "Analyst2", "1.1.1"),
        ("2023-06-01 24:35:25", "CEDEX BIO HT", 00000, "Analyst3", "1.2.2"),
    ],
)
def test_create_title(
    processing_time: str,
    model_number: str,
    device_serial: int,
    analyst: str,
    software_version: str,
) -> None:
    title_data = {
        "data processing time": processing_time,
        "model number": model_number,
        "device serial number": device_serial,
        "analyst": analyst,
        "software version": software_version,
    }
    title = Title.create(SeriesData(pd.Series(title_data)))

    assert title.data_processing_time == processing_time
    assert title.analyst == analyst
    assert title.model_number == model_number
    assert title.device_serial_number == str(device_serial)
    assert title.software_version == software_version


def test_create_title_with_no_analyst() -> None:
    title_data = SeriesData(
        pd.Series(
            {
                "device serial number": 1234,
                "data processing time": "2021-06-01 13:04:06",
            }
        )
    )
    with pytest.raises(
        AllotropeConversionError, match="Expected non-null value for analyst"
    ):
        Title.create(title_data)


def test_create_title_with_no_serial_number() -> None:
    title_data = SeriesData(
        pd.Series({"analyst": "dummy", "data processing time": "2021-06-01 13:04:06"})
    )
    with pytest.raises(
        AllotropeConversionError,
        match="Expected non-null value for device serial number.",
    ):
        Title.create(title_data)


def test_create_raw_measurement() -> None:
    data = SeriesData(
        pd.Series(
            {
                "analyte name": "glutamine",
                "measurement time": "2021-05-20T16:55:51+00:00",
                "concentration value": 2.45,
                "concentration unit": "mmol/L",
                "analyte code": "GLN2B",
            }
        )
    )
    measurement = RawMeasurement.create(data)
    assert measurement.name == "glutamine"
    assert measurement.measurement_time == "2021-05-20T16:55:51+00:00"
    assert measurement.concentration_value == 2.45
    assert measurement.unit == "mmol/L"
    assert measurement.analyte_code == "GLN2B"


def test_create_measurements() -> None:
    data = pd.DataFrame(
        {
            "analyte name": ["lactate", "glutamine", "osmolality"],
            "measurement time": [
                "2021-05-20T16:55:51+00:00",
                "2021-05-20T16:56:51+00:00",
                "2021-05-20T16:57:51+00:00",
            ],
            "concentration unit": ["g/L", "mmol/L", "mosm/kg"],
            "concentration value": [2.45, 4.35, 3.7448],
            "analyte code": ["LAC2B", "GLN2B", "OSM2B"],
        }
    )
    measurements = create_measurements(data)

    assert measurements == {
        "2021-05-20T16:55:51+00:00": {
            "lactate_LAC2B": RawMeasurement(
                "lactate", "2021-05-20T16:55:51+00:00", 2.45, "g/L", "LAC2B", None, {}
            ),
            "glutamine_GLN2B": RawMeasurement(
                "glutamine",
                "2021-05-20T16:56:51+00:00",
                4.35,
                "mmol/L",
                "GLN2B",
                None,
                {},
            ),
            "osmolality_OSM2B": RawMeasurement(
                "osmolality",
                "2021-05-20T16:57:51+00:00",
                3.7448,
                "mosm/kg",
                "OSM2B",
                None,
                {},
            ),
        }
    }


def test_create_measurements_more_than_one_measurement_docs() -> None:
    data = pd.DataFrame(
        {
            "analyte name": ["lactate", "glutamine", "glutamine"],
            "measurement time": [
                "2021-05-20T16:55:51+00:00",
                "2021-05-20T16:56:51+00:00",
                "2021-05-21T16:57:51+00:00",
            ],
            "concentration unit": ["g/L", "mmol/L", "mmol/L"],
            "concentration value": [2.45, 4.35, 3.45],
            "analyte code": ["LAC2B", "GLN2B", "GLN2B"],
        },
    )
    measurements = create_measurements(data)

    assert measurements == {
        "2021-05-20T16:55:51+00:00": {
            "lactate_LAC2B": RawMeasurement(
                "lactate", "2021-05-20T16:55:51+00:00", 2.45, "g/L", "LAC2B", None, {}
            ),
            "glutamine_GLN2B": RawMeasurement(
                "glutamine",
                "2021-05-20T16:56:51+00:00",
                4.35,
                "mmol/L",
                "GLN2B",
                None,
                {},
            ),
        },
        "2021-05-21T16:57:51+00:00": {
            "glutamine_GLN2B": RawMeasurement(
                "glutamine",
                "2021-05-21T16:57:51+00:00",
                3.45,
                "mmol/L",
                "GLN2B",
                None,
                {},
            ),
        },
    }


def test_create_measurements_duplicate_measurements() -> None:
    data = pd.DataFrame(
        {
            "analyte name": ["lactate", "glutamine", "glutamine"],
            "measurement time": [
                "2021-05-20T16:55:51+00:00",
                "2021-05-20T16:56:51+00:00",
                "2021-05-20T16:57:51+00:00",
            ],
            "concentration unit": ["g/L", "mmol/L", "mmol/L"],
            "concentration value": [2.45, 4.35, 3.45],
            "analyte code": ["LAC2B", "GLN2B", "GLN2B"],
        },
    )

    with pytest.raises(
        AllotropyParserError,
        match="Duplicate measurement for GLN2B in the same measurement group. 3.45 vs 4.35",
    ):
        create_measurements(data)


def test_create_sample() -> None:
    sample_data = pd.DataFrame(
        {
            "sample identifier": ["PPDTEST1", "PPDTEST1"],
            "batch identifier": ["batch_id", "batch_id"],
            "analyte name": ["glutamine", "lactate"],
            "concentration unit": ["mmol/L", "g/L"],
            "concentration value": [4.35, 2.45],
            "sample role type": ["Sample", "Sample"],
            "measurement time": [
                "2021-05-20 16:56:51",
                "2021-05-20 16:55:51",
            ],
            "analyte code": ["GLN2B", "LAC2B"],
        }
    )
    sample = Sample.create(
        name="PPDTEST1",
        batch="batch_id",
        sample_data=sample_data,
    )
    assert sample.name == "PPDTEST1"
    assert sample.batch == "batch_id"
    assert sample.measurements == {
        "2021-05-20 16:55:51": {
            "lactate_LAC2B": RawMeasurement(
                "lactate", "2021-05-20 16:55:51", 2.45, "g/L", "LAC2B", None, {}
            ),
            "glutamine_GLN2B": RawMeasurement(
                "glutamine", "2021-05-20 16:56:51", 4.35, "mmol/L", "GLN2B", None, {}
            ),
        }
    }
