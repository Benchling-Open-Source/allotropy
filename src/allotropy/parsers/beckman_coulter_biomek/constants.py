from enum import Enum

DISPLAY_NAME = "Beckman Coulter Biomek"
DEVICE_TYPE = "liquid handler"
PROBE_HEAD_DEVICE_TYPE = "liquid handler probe head"
PRODUCT_MANUFACTURER = "Beckman Coulter"
SOFTWARE_NAME = "BioMek Software"


class TransferStep(str, Enum):
    ASPIRATE = "Aspirate"
    DISPENSE = "Dispense"


class FileFormat(str, Enum):
    UNIFIED_PIPETTING = "unified_pipetting"
    UNIFIED_TRANSFER = "unified_transfer"
    PIPETTING = "pipetting"


# Column mappings for different file formats
UNIFIED_PIPETTING_COLUMNS = [
    "Time Stamp",
    "Pod",
    "Transfer Step",
    "Deck Position",
    "Labware Name",
    "Labware Barcode",
    "Well Index",
    "Sample Name",
    "Probe",
    "Amount",
    "Liquid Handling Technique",
]

UNIFIED_TRANSFER_COLUMNS = [
    "Time Stamp",
    "Pod",
    "Source Position",
    "Source Labware Name",
    "Source Labware Barcode",
    "Source Well Index",
    "Sample Name",
    "Destination Position",
    "Destination Labware Name",
    "Destination Labware Barcode",
    "Destination Well Index",
    "Destination Sample Name",
    "Probe",
    "Amount",
]

PIPETTING_COLUMNS = [
    "Time Stamp",
    "Pod",
    "Transfer Step",
    "Position",
    "Labware Name",
    "Labware Barcode",
    "Well Index",
    "Amount",
    "Liquid Handling Technique",
]
