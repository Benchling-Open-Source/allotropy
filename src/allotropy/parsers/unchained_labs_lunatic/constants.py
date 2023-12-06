import re

WAVELENGHT_COLUMNS_RE = re.compile(r"^A[0-9]{3}$")
NO_WAVELENGHT_COLUMN_ERROR_MSG = (
    "The file is required to include an absorbance measurement column (e.g. A280)"
)
INCORRECT_WAVELENGHT_COLUMN_FORMAT_ERROR_MSG = (
    msg
) = "The wavelenght_column should follow the pattern A### (ex. A260)."
NO_DATE_OR_TIME_ERROR_MSG = (
    "The file is required to include both 'Date' and 'Time' columns."
)
