from enum import Enum

DISPLAY_NAME = "Beckman Coulter Biomek"
DEVICE_TYPE = "liquid handler"
PROBE_HEAD_DEVICE_TYPE = "liquid handler probe head"
PRODUCT_MANUFACTURER = "Beckman Coulter"
SOFTWARE_NAME = "BioMek Software"


class TransferStep(str, Enum):
    ASPIRATE = "Aspirate"
    DISPENSE = "Dispense"
