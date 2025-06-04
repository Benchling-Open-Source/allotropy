from allotropy.allotrope.models.shared.definitions.definitions import (
    TStatisticDatumRole,
)

DEFAULT_SOFTWARE_NAME = "xPONENT"
DEFAULT_CONTAINER_TYPE = "well plate"
DEFAULT_DEVICE_TYPE = "multi analyte profiling analyzer"

LUMINEX_EMPTY_PATTERN = r"^[,\"\s]*$"
CALIBRATION_BLOCK_HEADER = "Most Recent Calibration and (Control|Verification) Results"
TABLE_HEADER_PATTERN = '^"?DataType:"?,"?([^,"]*)"?'
MINIMUM_CALIBRATION_LINE_COLS = 2
EXPECTED_CALIBRATION_RESULT_LEN = 2
EXPECTED_HEADER_COLUMNS = 7
REQUIRED_SECTIONS = ["Count", "Units", "Dilution Factor"]

STATISTIC_SECTIONS_CONF = {
    "Median": {
        "role": TStatisticDatumRole.median_role,
        "unit": "RFU",
    },
    "Mean": {
        "role": TStatisticDatumRole.arithmetic_mean_role,
        "unit": "RFU",
    },
    "% CV": {
        "role": TStatisticDatumRole.coefficient_of_variation_role,
        "unit": "(unitless)",
    },
    "Standard Deviation": {
        "role": TStatisticDatumRole.standard_deviation_role,
        "unit": "(unitless)",
    },
    "Peak": {
        "role": TStatisticDatumRole.mode_value_role,
        "unit": "RFU",
    },
    "Trimmed Peak": {
        "role": TStatisticDatumRole.trimmed_mode_role,
        "unit": "RFU",
    },
    "Trimmed Count": {
        "role": TStatisticDatumRole.trimmed_count_role,
        "unit": "RFU",
    },
    "Trimmed Standard Deviation": {
        "role": TStatisticDatumRole.trimmed_standard_deviation_role,
        "unit": "(unitless)",
    },
    "Trimmed Mean": {
        "role": TStatisticDatumRole.trimmed_arithmetic_mean_role,
        "unit": "RFU",
    },
}
