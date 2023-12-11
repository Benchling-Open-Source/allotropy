import re

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
