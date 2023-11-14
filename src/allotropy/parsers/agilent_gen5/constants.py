from enum import Enum
from typing import Optional


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
