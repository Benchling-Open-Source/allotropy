from enum import Enum

MULTIPLATE_FILE_ERROR = "Only a single plate per file can be processed at this time. Please refer to Gen5 documentation for how to generate single plate exports from multi-plate experiments"
NO_PLATE_DATA_ERROR = "No plate data found in file."
UNSUPORTED_READ_TYPE_ERROR = "Only Endpoint measurements can be processed at this time."
UNSUPORTED_READ_TYPE_ERROR = "Only imaging results can be processed at this time."

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

DEFAULT_SOFTWARE_NAME = "Gen5 Image"
DEVICE_TYPE = "plate reader"

FILENAME_REGEX = r"^\d{6}_\d{6}_(?P<plate_identifier>.[^_]*)_.*\.txt$"


class ImageMode(str, Enum):
    SINGLE_IMAGE = "Image Single Image"
    MONTAGE = "Image Montage"
    Z_STACKING = "Image Z-stacking"


class ReadType(str, Enum):
    ENDPOINT = "Endpoint"
    KINETIC = "Kinetic"
    AREASCAN = "Area Scan"
    SPECTRAL = "Spectral"
    IMAGE = "Image"
