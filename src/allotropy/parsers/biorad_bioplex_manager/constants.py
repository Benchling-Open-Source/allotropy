from dataclasses import dataclass

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.models.shared.definitions.definitions import (
    TStatisticDatumRole,
)

SOFTWARE_NAME = "Bio-Plex Manager"
PRODUCT_MANUFACTURER = "Bio-Rad"
DEVICE_TYPE = "multi analyte profiling analyzer"
CONTAINER_TYPE = "well plate"

ERROR_MAPPING = {
    "1": "Low bead number",
    "2": "Aggregated beads",
    "3": "Classify efficiency",
    "4": "Region selection",
    "5": "Platform temperature",
}

SAMPLE_ROLE_TYPE_MAPPING = {
    "Blank": SampleRoleType.blank_role,
    "Control": SampleRoleType.control_sample_role,
    "Standard": SampleRoleType.standard_sample_role,
    "Unknown": SampleRoleType.unknown_sample_role,
}

EXPECTED_TAGS = [
    "Samples",
    "NativeDocumentLocation",
    "Description",
    "PlateDimensions",
    "Wells",
]


@dataclass(frozen=True)
class StatisticSectionConfig:
    role: TStatisticDatumRole
    unit: str


# Statistics mapping for Bio-Rad BioPlex XML elements
STATISTIC_SECTIONS_CONF = {
    "Median": StatisticSectionConfig(
        role=TStatisticDatumRole.median_role,
        unit="RFU",
    ),
    "Mean": StatisticSectionConfig(
        role=TStatisticDatumRole.arithmetic_mean_role,
        unit="RFU",
    ),
    "CV": StatisticSectionConfig(
        role=TStatisticDatumRole.coefficient_of_variation_role,
        unit="(unitless)",
    ),
    "StdDev": StatisticSectionConfig(
        role=TStatisticDatumRole.standard_deviation_role,
        unit="(unitless)",
    ),
    "TrimmedMean": StatisticSectionConfig(
        role=TStatisticDatumRole.trimmed_arithmetic_mean_role,
        unit="RFU",
    ),
    "TrimmedStdDev": StatisticSectionConfig(
        role=TStatisticDatumRole.trimmed_standard_deviation_role,
        unit="(unitless)",
    ),
    # "StdErr": StatisticSectionConfig(
    #     role=TStatisticDatumRole.standard_error_role,
    #     unit="RFU",
    # ),
    # "TrimmedCV": StatisticSectionConfig(
    #     role=TStatisticDatumRole.trimmed_coefficient_of_variation_role,
    #     unit="(unitless)",
    # ),
    # Note: StdErr (standard error) and TrimmedCV (trimmed coefficient of variation)
    # are not supported yet
}
