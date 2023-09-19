from enum import Enum


class XrVersion(str, Enum):
    _2_06 = "2.06"
    _2_04 = "2.04"


DATE_HEADER = {
    XrVersion._2_06: "Sample date/time",
    XrVersion._2_04: "Sample date",
}

MODEL_RE = r"Vi-CELL XR (?P<version>\d{1,}\.\d{2,}(.\d{1,})?)"
DEFAULT_VERSION = XrVersion._2_06

DEFAULT_ANALYST = "Vi-Cell XR"
MODEL_NUMBER = "Vi-Cell XR"
SOFTWARE_NAME = "Vi-Cell XR"
