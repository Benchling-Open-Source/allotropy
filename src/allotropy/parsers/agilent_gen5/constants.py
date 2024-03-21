from enum import Enum
from typing import Optional

MULTIPLATE_FILE_ERROR = "Only a single plate per file can be processed at this time. Please refer to Gen5 documentation for how to generate single plate exports from multi-plate experiments"
NO_PLATE_DATA_ERROR = "No plate data found in file."
UNSUPORTED_READ_TYPE_ERROR = "Only Endpoint measurements can be processed at this time."

EMISSION_KEY = "Emission"
EXCITATION_KEY = "Excitation"
GAIN_KEY = "Gain"
OPTICS_KEY = "Optics"
MEASUREMENTS_DATA_POINT_KEY = "Measurements/Data Point"
MIRROR_KEY = "Mirror"
READ_HEIGHT_KEY = "Read Height"
READ_SPEED_KEY = "Read Speed"


class ReadMode(str, Enum):
    ABSORBANCE = "Absorbance"
    FLUORESCENCE = "Fluorescence"
    LUMINESCENCE = "Luminescence"


class ReadType(str, Enum):
    ENDPOINT = "Endpoint"
    KINETIC = "Kinetic"
    AREASCAN = "Area Scan"
    SPECTRAL = "Spectral"


READTYPE_TO_DIMENSIONS: dict[ReadType, list[tuple[str, str, Optional[str]]]] = {
    ReadType.ENDPOINT: [("int", "wavelength", "nm")],
    ReadType.KINETIC: [("double", "time", "s")],
    ReadType.AREASCAN: [
        ("int", "x", None),
        ("int", "y", None),
    ],
    ReadType.SPECTRAL: [("int", "wavelength", "nm")],
}
