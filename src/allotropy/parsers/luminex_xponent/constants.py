from dataclasses import dataclass

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


@dataclass(frozen=True)
class StatisticSectionConfig:
    role: TStatisticDatumRole
    unit: str


STATISTIC_SECTIONS_CONF = {
    "Median": StatisticSectionConfig(
        role=TStatisticDatumRole.median_role,
        unit="RFU",
    ),
    "Mean": StatisticSectionConfig(
        role=TStatisticDatumRole.arithmetic_mean_role,
        unit="RFU",
    ),
    "%CV": StatisticSectionConfig(
        role=TStatisticDatumRole.coefficient_of_variation_role,
        unit="(unitless)",
    ),
    "Standard Deviation": StatisticSectionConfig(
        role=TStatisticDatumRole.standard_deviation_role,
        unit="(unitless)",
    ),
    "Peak": StatisticSectionConfig(
        role=TStatisticDatumRole.mode_value_role,
        unit="RFU",
    ),
    "Trimmed Peak": StatisticSectionConfig(
        role=TStatisticDatumRole.trimmed_mode_value_role,
        unit="RFU",
    ),
    "Trimmed Count": StatisticSectionConfig(
        role=TStatisticDatumRole.trimmed_count_role,
        unit="RFU",
    ),
    "Trimmed Standard Deviation": StatisticSectionConfig(
        role=TStatisticDatumRole.trimmed_standard_deviation_role,
        unit="(unitless)",
    ),
    "Trimmed Mean": StatisticSectionConfig(
        role=TStatisticDatumRole.trimmed_arithmetic_mean_role,
        unit="RFU",
    ),
}

CALCULATED_DATA_SECTIONS: dict[str, str] = {
    "Net MFI": "RFU",
    "Avg Net MFI": "RFU",
    "Test Result": "(unitless)",
    "% Recovery": "(unitless)",
    "%CV of Replicates": "(unitless)",
}
