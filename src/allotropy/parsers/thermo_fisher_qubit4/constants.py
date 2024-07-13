""" Constants file for ThermoFisher Qubit 4 Adapter"""

# Instrument Software Details
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicrogramPerMicroliter,
    TQuantityValueMicrogramPerMilliliter,
    TQuantityValueMilligramPerMilliliter,
    TQuantityValueNanogramPerMicroliter,
    TQuantityValueNanogramPerMilliliter,
)

QUBIT_SOFTWARE = "Qubit 4 software"
MODEL_NUMBER = "Qubit 4"
BRAND_NAME = "Qubit"
PRODUCT_MANUFACTURER = "Thermo Fisher Scientific"
DEVICE_TYPE = "fluorescence detector"
DISPLAY_NAME = "Thermo Fisher Qubit 4"

# Errors
VALUE_ERROR = "Unable to find value for column"
UNSUPPORTED_FILE_FORMAT_ERROR = "Unsupported file format. Expected xlsx. Actual: "
UNSUPPORTED_WAVELENGTH_ERROR = (
    "Unsupported wavelength. Expected Green or Far red. Actual: "
)

CONCENTRATION_UNIT_TO_TQUANTITY = {
    "μg/μL": TQuantityValueMicrogramPerMicroliter,
    "μg/mL": TQuantityValueMicrogramPerMilliliter,
    "mg/mL": TQuantityValueMilligramPerMilliliter,
    "ng/µL": TQuantityValueNanogramPerMicroliter,
    "ng/mL": TQuantityValueNanogramPerMilliliter,
}
