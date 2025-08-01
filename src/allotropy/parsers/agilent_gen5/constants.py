from enum import Enum

MULTIPLATE_FILE_ERROR = "Only a single plate per file can be processed at this time. Please refer to Gen5 documentation for how to generate single plate exports from multi-plate experiments"
NO_PLATE_DATA_ERROR = "No plate data found in file."
UNSUPPORTED_READ_TYPE_ERROR = (
    "Only Endpoint measurements can be processed at this time."
)
NO_MEASUREMENTS_ERROR = "Invalid data - the file contains invalid or missing measurement data. Unable to construct ASM."

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
FIXED_EXCITATION_KEY = "Fixed Excitation"
FIXED_EMISSION_KEY = "Fixed Emission"
EMISSION_START_KEY = "Emission Start"
EXCITATION_START_KEY = "Excitation Start"
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
LIGHT_DIRECTIONS = ["Parallel", "Perpendicular"]


class ReadMode(str, Enum):
    ABSORBANCE = "Absorbance"
    FLUORESCENCE = "Fluorescence"
    LUMINESCENCE = "Luminescence"
    ALPHALISA = "Alpha"


UNSUPPORTED_READ_MODE_ERROR = (
    f"Read mode not found; expected to find one of {sorted(ReadMode._member_names_)}."
)
ELAPSED_TIME = "elapsed time"

READ_DATA_MEASUREMENT_ERROR = "No read mode found for measurement {}"
ALPHALISA_FLUORESCENCE_FOUND = (
    "Both ALPHALISA and FLUORESCENCE read modes detected, which is not supported."
)

DATA_SOURCE_FEATURE_VALUES = {
    ReadMode.ABSORBANCE: "absorption profile data cube",
    ReadMode.FLUORESCENCE: "fluorescence emission profile data cube",
    ReadMode.LUMINESCENCE: "luminescence profile data cube",
}

READ_MODE_UNITS = {
    ReadMode.ABSORBANCE: "mAU",
    ReadMode.FLUORESCENCE: "RFU",
    ReadMode.LUMINESCENCE: "RLU",
}
SECONDS = "s"


class ReadType(str, Enum):
    ENDPOINT = "Endpoint"
    AREASCAN = "Area Scan"
    SPECTRUM = "Spectrum"
