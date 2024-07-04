""" Constants file for Thermo Fisher Scientific Qubit FLex Parser"""

from allotropy.__about__ import __version__

ASM_CONVERTER_NAME = "allotropy"
ASM_CONVERTER_VERSION = __version__

# Value to use for encoding str params when we want to use chardet to detect the encoding.
CHARDET_ENCODING = "chardet"

DEFAULT_ENCODING = "UTF-8"

SOFTWARE_NAME = "Qubit Flex software"
MODEL_NUMBER = "Qubit Flex"
PRODUCT_MANUFACTURER = "Thermo Fisher Scientific"
BRAND_NAME= "Qubit"
DEVICE_TYPE = "fluorescence detector"
DISPLAY_NAME = "Thermo Fisher Qubit Flex"
CONTAINER_TYPE = "tube"


UNSUPPORTED_FILE_FORMAT_ERROR = (
    "Unsupported file format. Expected xlsx or csv file. Actual: "
)