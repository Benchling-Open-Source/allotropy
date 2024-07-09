from enum import Enum

MULTIPLATE_FILE_ERROR = "Only a single plate per file can be processed at this time. Please refer to Gen5 documentation for how to generate single plate exports from multi-plate experiments"
NO_PLATE_DATA_ERROR = "No plate data found in file."
UNSUPORTED_READ_TYPE_ERROR = "Only Endpoint measurements can be processed at this time."

HEADER_PREFIXES = frozenset(
    {
        "Software Version",
        "Experiment File Path:",
        "Protocol File Path:",
        "Plate Number",
        "Date",
        "Time",
        "Reader Type:",
        "Reader Serial Number:",
        "Reading Type",
    },
)


EMISSION_KEY = "Emission"
EXCITATION_KEY = "Excitation"
GAIN_KEY = "Gain"
OPTICS_KEY = "Optics"
MEASUREMENTS_DATA_POINT_KEY = "Measurements/Data Point"
MIRROR_KEY = "Mirror"
PATHLENGTH_CORRECTION_KEY = "Pathlength Correction"
READ_HEIGHT_KEY = "Read Height"
READ_SPEED_KEY = "Read Speed"
WAVELENGTHS_KEY = "Wavelengths"

DEFAULT_SOFTWARE_NAME = "Gen5"
DEVICE_TYPE = "plate reader"

FILENAME_REGEX = r"^\d{6}_\d{6}_(?P<plate_identifier>.[^_]*)_.*\.txt$"

NAN_EMISSION_EXCITATION = ["Full light", "Plug", "Hole"]


class ReadMode(str, Enum):
    ABSORBANCE = "Absorbance"
    FLUORESCENCE = "Fluorescence"
    LUMINESCENCE = "Luminescence"
    ALPHALISA = "Alpha"


class ReadType(str, Enum):
    ENDPOINT = "Endpoint"
    KINETIC = "Kinetic"
    AREASCAN = "Area Scan"
    SPECTRAL = "Spectral"
