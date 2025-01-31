DEFAULT_SOFTWARE_NAME = "xPONENT"
DEFAULT_CONTAINER_TYPE = "well plate"
DEFAULT_DEVICE_TYPE = "multi analyte profiling analyzer"

LUMINEX_EMPTY_PATTERN = r"^[,\"\s]*$"
CALIBRATION_BLOCK_HEADER = "Most Recent Calibration and (Control|Verification) Results"
TABLE_HEADER_PATTERN = '^"?DataType:"?,"?([^,"]*)"?'
MINIMUM_CALIBRATION_LINE_COLS = 2
EXPECTED_CALIBRATION_RESULT_LEN = 2
EXPECTED_HEADER_COLUMNS = 7
REQUIRED_SECTIONS = ["Median", "Count", "Units", "Dilution Factor"]
