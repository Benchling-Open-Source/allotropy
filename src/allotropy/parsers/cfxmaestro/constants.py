from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ContainerType

DISPLAY_NAME = "Bio-Rad CFX Maestro"
DEVICE_TYPE = "qPCR"

PRODUCT_MANUFACTURER = "Bio-Rad"
SOFTWARE_NAME = "CFX Maestro"
CONTAINER_TYPE = ContainerType.well_plate

SAMPLE_DOCUMENT_CUSTOM_KEYS = {
    "Starting Quantity \\(SQ\\)",
    "Log Starting Quantity",
    "SQ Std. Dev",
    "SQ Mean",
    "Well Note",
}

DEVICE_CONTROL_DOCUMENT_CUSTOM_KEYS = {
    "Set Point",
}

PROCESSED_DATA_DOCUMENT_CUSTOM_KEYS = {
    "Cq Std. Dev",
}
