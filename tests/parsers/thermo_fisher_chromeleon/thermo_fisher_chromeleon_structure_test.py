from typing import Any

import pytest

from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Metadata,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.thermo_fisher_chromeleon import constants
from allotropy.parsers.thermo_fisher_chromeleon.thermo_fisher_chromeleon_structure import (
    create_measurement_groups,
    create_metadata,
)


@pytest.fixture
def mock_data() -> dict[str, Any]:
    return {
        "device information": {
            "pump model number": "HPG-3200RS",
            "uv model number": "DAD-3000RS",
            "sampler model number": "WPS-3000RS",
        },
        "injections": [
            {
                "injection number": 1,
                "injection name": "Blank",
                "injection identifier": "bee79522-5ead-406e-a656-66534b588357",
                "injection time": "2011-07-15T16:27:39+01:00",
                "injection position": "RA1",
                "injection status": "Finished",
                "injection type": "Blank",
                "precondition system instrument name": "Instrument123",
                "description": "Test injection description",
                "sample identifier": "",
                "location identifier": "RA1",
                "last update user name": "anatoliy.kolesnick",
                "creation user name": "anatoliy.kolesnick",
                "detection type": "single channel",
                "injection volume setting": 10.0,
                "injection volume setting unit": "\u00b5l",
                "custom variables": {},
                "signals": [
                    {
                        "signal name": "UV_VIS_1",
                        "detection type": "single channel",
                        "detector sampling rate setting": "unknown",
                        "detector offset setting": "unknown",
                        "bandwidth setting": 1.0,
                        "wavelength setting": 230.0,
                        "reference bandwidth setting": 1.0,
                        "reference wavelength setting": 0.0,
                        "chromatogram": {
                            "x": [
                                0.0,
                                0.16,
                            ],
                            "y": [
                                0.0,
                                -1.014,
                            ],
                        },
                        "peaks": [
                            {
                                "name": "Substance 1",
                                "identifier": "1",
                                "start time": 0.14766666666666667,
                                "end time": 0.23966666666666667,
                                "area": 3.048328868007354,
                                "height": 111.28958058334837,
                                "relative peak area": 40.9093439254137,
                                "relative peak height": 41.19251735685675,
                                "peak width at 5 % of height": 0.05369982639959206,
                                "asymmetry factor measured at 5 % height": 1.2188763229155313,
                                "retention time": 0.19233333333333336,
                                "relative retention time": 9,
                                "capacity factor": 12,
                                "number of theoretical plates by peak width at half height": 312.0,
                                "amount": 100.0,
                                "calibration coefficient 0": 0.0,
                                "calibration coefficient 1": 0.030483288680073543,
                                "calibration coefficient 2": 0.0,
                                "calibration type": None,
                                "number of calibration points": 4.0,
                                "relative standard deviation": 0.0,
                                "relative area group": 40.9093439254137,
                                "chromatographic peak resolution": 1.7448475391025424,
                                "chromatographic peak resolution (USP)": 1.7453679568237164,
                                "peak type": None,
                                "peak width at baseline": 0.043406610942765905,
                                "peak width at half height": 0.025608762442017846,
                            },
                        ],
                    }
                ],
            },
        ],
        "first_injection": {},
        "sequence": {
            "sequence creation time": "2024-02-17 12:00:00",
            "sequence directory": "/path/to/sequence",
            "sequence name": "Test Sequence",
            "sequence update operator": "Operator XYZ",
            "sequence update time": "2024-02-17 13:00:00",
            "number of injections": 5,
        },
    }


def test_create_metadata(mock_data: dict[str, Any]) -> None:
    metadata = create_metadata(
        first_injection=mock_data["injections"][0],
        sequence=mock_data["sequence"],
        file_path="/data/test_file.json",
    )

    assert isinstance(metadata, Metadata)
    assert metadata.asset_management_identifier == "Instrument123"
    assert metadata.software_name == constants.SOFTWARE_NAME
    assert metadata.file_name == "test_file.json"
    assert metadata.unc_path == "/data/test_file.json"
    assert metadata.description == "Test injection description"
    assert metadata.lc_agg_custom_info == {
        "Sequence Creation Time": "2024-02-17 12:00:00",
        "Sequence Directory": "/path/to/sequence",
        "Sequence Name": "Test Sequence",
        "Sequence Update operator": "Operator XYZ",
        "Sequence Update Time": "2024-02-17 13:00:00",
        "Number of Injections": 5,
    }


def test_create_measurement_groups(mock_data: dict[str, Any]) -> None:
    measurement_groups = create_measurement_groups(
        injections=mock_data["injections"],
    )
    measurement = measurement_groups[0].measurements[0]
    assert measurement.chromatography_serial_num == NOT_APPLICABLE
    assert measurement.description == "Test injection description"
    assert measurement.injection_identifier == "bee79522-5ead-406e-a656-66534b588357"
    assert measurement.injection_time == "2011-07-15T16:27:39+01:00"
    assert measurement.injection_volume_setting == 10.0
    assert measurement.location_identifier == "RA1"
    assert measurement.injection_custom_info is not None
    assert (
        measurement.injection_custom_info["creation user name"] == "anatoliy.kolesnick"
    )
    assert (
        measurement.injection_custom_info["last update user name"]
        == "anatoliy.kolesnick"
    )
    assert measurement.injection_custom_info["injection"] == 1
    assert measurement.injection_custom_info["injection name"] == "Blank"
    assert measurement.injection_custom_info["injection position"] == "RA1"
    assert measurement.injection_custom_info["injection status"] == "Finished"
    assert measurement.injection_custom_info["injection type"] == "Blank"

    device_control_doc = measurement.device_control_docs[0]
    assert device_control_doc is not None
    assert device_control_doc.device_type == constants.DEVICE_TYPE
    assert device_control_doc.detection_type == "single channel"
    assert device_control_doc.electronic_absorbance_reference_bandwidth_setting == 1.0
    assert device_control_doc.electronic_absorbance_reference_wavelength_setting == 0.0

    peaks = measurement.peaks
    assert peaks is not None
    peak = peaks[0]
    assert peak.peak_analyte_amount == 100.0
    assert peak.area == 0.0030483288680073542
    assert peak.asymmetry_factor_measured_at_5_percent_height == 1.2188763229155313
    assert peak.area_unit == "mAU.s"
    assert peak.capacity_factor == 12
    assert peak.chromatographic_resolution == 1.7448475391025424
    assert peak.end == 14.38
    assert peak.start == 8.86
    assert peak.height == 0.11128958058334837
    assert peak.end_unit == "s"
    assert peak.start_unit == "s"
    assert peak.index == "1"
    assert peak.number_of_theoretical_plates_by_peak_width_at_half_height == 312.0
    assert peak.peak_width_at_5_percent_of_height == 3.2219895839755237
    assert peak.peak_width_at_baseline == 2.6043966565659544
    assert peak.relative_height == 41.19251735685675
    assert peak.retention_time == 11.540000000000001
    assert peak.relative_retention_time == 9
    assert peak.width_at_half_height == 1.5365257465210709
    assert peak.written_name == "Substance 1"
