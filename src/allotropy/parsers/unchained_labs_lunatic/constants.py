import re

from allotropy.allotrope.models.shared.definitions.units import UNITLESS

WAVELENGTH_COLUMNS_RE = re.compile(r"^A\d{3}$")
NO_WAVELENGTH_COLUMN_ERROR_MSG = (
    "The file is required to include an absorbance measurement column (e.g. A280)"
)
INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG = (
    msg
) = "The wavelength_column should follow the pattern A### (ex. A260)."
NO_DATE_OR_TIME_ERROR_MSG = (
    "The file is required to include both 'Date' and 'Time' columns."
)
NO_MEASUREMENT_IN_PLATE_ERROR_MSG = (
    "The plate data does not contain absorbance measurement for {}."
)

CALCULATED_DATA_LOOKUP = {
    "A260": [
        {
            "column": "A260 Concentration (ng/ul)",
            "name": "Concentration",
            "feature": "absorbance",
            "unit": "ng/µL",
        },
        {
            "column": "Concentration (ng/ul)",
            "name": "Concentration",
            "feature": "absorbance",
            "unit": "ng/µL",
        },
        {
            "column": "Background (A260)",
            "name": "Background (A260)",
            "feature": "absorbance",
            "unit": "mAU",
        },
        {
            "column": "A260/A230",
            "name": "A260/A230",
            "feature": "absorbance",
            "unit": UNITLESS,
        },
        {
            "column": "A260/A280",
            "name": "A260/A280",
            "feature": "absorbance",
            "unit": UNITLESS,
        },
    ],
    "A280": [
        {
            "column": "Concentration (mg/ml)",
            "name": "Concentration",
            "feature": "absorbance",
            "unit": "mg/mL",
        },
        {
            "column": "Background (A280)",
            "name": "Background (A280)",
            "feature": "absorbance",
            "unit": "mAU",
        },
        {
            "column": "A260/A280",
            "name": "A260/A280",
            "feature": "absorbance",
            "unit": UNITLESS,
        },
    ],
}
