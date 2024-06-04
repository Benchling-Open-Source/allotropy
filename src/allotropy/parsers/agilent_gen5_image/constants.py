from enum import Enum

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    TransmittedLightSetting,
)

MULTIPLATE_FILE_ERROR = "Only a single plate per file can be processed at this time. Please refer to Gen5 documentation for how to generate single plate exports from multi-plate experiments"
NO_PLATE_DATA_ERROR = "No plate data found in file."
UNSUPORTED_READ_TYPE_ERROR = "Only imaging results can be processed at this time."
DEFAULT_EXPORT_FORMAT_ERROR = "This export format cannot be processed at this time - ensure the 'Regroup data in one matrix/table' option is enable within Gen5"

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
DEVICE_TYPE = "Imager"
DETECTION_TYPE = "optical-imaging"

AUTOFOCUS_STRINGS = frozenset(
    {
        "Laser autofocus",
        "Autofocus with optional scan",
        "Autofocus without optional scan",
    }
)

DETECTOR_DISTANCE_REGEX = r"Fixed focal height at bottom elevation plus (-?[\d\.]+) \w."
CHANNEL_HEADER_REGEX = r"\tChannel \d+:  (?P<fluorescent_tag>.+) (?P<excitation_wavelength>\d{3}),(?P<detector_wavelength>\d{3})"
FILENAME_REGEX = r"^\d{6}_\d{6}_(?P<plate_identifier>.[^_]*)_.*\.txt$"
SETTINGS_SECTION_REGEX = r"^\tChannel|^\tColor Camera"

TRANSMITTED_LIGHT_MAP = {
    "Brightfield": TransmittedLightSetting.brightfield,
    "Phase Contrast": TransmittedLightSetting.phase_contrast,
    "Transmitted Light": TransmittedLightSetting.brightfield,
    "Reflected Light": TransmittedLightSetting.brightfield,
    "Color Bright Field": TransmittedLightSetting.brightfield,
}


class DetectionType(str, Enum):
    SINGLE_IMAGE = "Image Single Image"
    MONTAGE = "Image Montage"
    Z_STACK = "Image Z-Stack"


class ReadType(str, Enum):
    ENDPOINT = "Endpoint"
    KINETIC = "Kinetic"
    AREASCAN = "Area Scan"
    SPECTRAL = "Spectral"
    IMAGE = "Image"
