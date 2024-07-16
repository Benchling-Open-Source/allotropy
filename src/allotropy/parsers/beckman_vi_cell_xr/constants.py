from enum import Enum


class XrVersion(str, Enum):
    _2_06 = "2.06"
    _2_04 = "2.04"


DATE_HEADER = "Sample date"

HEADINGS_TO_PARSER_HEADINGS = {
    "RunDate": DATE_HEADER,
    "Sample date/time": DATE_HEADER,
    # NOTE: data here is a typo in the Beckman software.
    "Sample data/time": DATE_HEADER,
    "Dilution": "Dilution factor",
    "Total cells / ml (x 10^6)": "Total cells/ml (x10^6)",
    "Average diameter (microns)": "Avg. diam. (microns)",
    "Average circularity": "Avg. circ.",
    "Total viable cells / ml (x 10^6)": "Viable cells/ml (x10^6)",
}

MODEL_RE = r"Vi-CELL XR (?P<version>\d{1,}\.\d{2,}(.\d{1,})?)"
DEFAULT_VERSION = XrVersion._2_06

DEFAULT_ANALYST = "Vi-Cell XR"
MODEL_NUMBER = "Vi-Cell XR"
SOFTWARE_NAME = "Vi-Cell XR"
