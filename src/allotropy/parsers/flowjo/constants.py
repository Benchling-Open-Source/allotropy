from enum import Enum

from allotropy.allotrope.models.shared.definitions.definitions import (
    TStatisticDatumRole,
)

# FlowJo parser constants
DEVICE_IDENTIFIER = "cytometer"
DEVICE_TYPE = "Flow Cytometer"
SOFTWARE_NAME = "FlowJo"
DISPLAY_NAME = "FlowJo"

# Equipment serial number keywords
EQUIPMENT_SERIAL_KEYWORDS = {"CTNUM", "$CYTSN"}

# Keywords extracted at measurement document level (custom_info)
MEASUREMENT_DOCUMENT_KEYWORDS = {
    "$INST",
    "FJ_FCS_VERSION",
    "$BEGINANALYSIS",
    "$ENDANALYSIS",
    "$BEGINSTEXT",
    "$ENDSTEXT",
    "$BEGINDATA",
    "$ENDDATA",
    "$FIL",
    "$SYS",
    "$TOT",
    "$PAR",
    "$MODE",
    "$BYTEORD",
    "$DATATYPE",
    "$NEXTDATA",
    "CREATOR",
    "$SRC",
    "EXPERIMENT NAME",
    "GUID",
    "$DATE",
    "$BTIM",
    "$ETIM",
    "SETTINGS",
    "WINDOW EXTENSION",
    "EXPORT USER NAME",
    "EXPORT TIME",
    "modDate",
    "name",
    "clientTimestamp",
    "homepage",
}

# Keywords extracted at sample document level (custom_info)
SAMPLE_DOCUMENT_KEYWORDS = {"TUBE NAME"}

# Keywords extracted at processed data document level (custom_info)
PROCESSED_DATA_KEYWORDS = {
    "linFromKW",
    "logFromKW",
    "linMax",
    "logMax",
    "useFCS3",
    "useGain",
    "linearRescale",
    "THRESHOLD",
    "APPLY COMPENSATION",
    "$TIMESTEP",
    "FSC ASF",
    "AUTOBS",
    "SPILL",
    "logMin",
    "linMin",
    "extraNegs",
    "logRescale",
}

# Combined set of all structured keywords (for exclusion logic)
ALL_STRUCTURED_KEYWORDS = (
    MEASUREMENT_DOCUMENT_KEYWORDS
    | SAMPLE_DOCUMENT_KEYWORDS
    | PROCESSED_DATA_KEYWORDS
    | EQUIPMENT_SERIAL_KEYWORDS
    | {
        "$OP",
        "WELL ID",
        "PLATE ID",
        "$CYT",
        "CYTNUM",
        "curGroup",
    }  # Other keywords used elsewhere
)

# Map of FlowJo field names to statistic datum roles and units
FLOWJO_STATISTIC_MAP = {
    # Fluorescence statistics
    "Median": {"role": TStatisticDatumRole.median_role.value, "unit": "RFU"},
    "CV": {
        "role": TStatisticDatumRole.coefficient_of_variation_role.value,
        "unit": "%",
    },
    "Robust CV": {
        "role": TStatisticDatumRole.robust_coefficient_of_variation_role.value,
        "unit": "%",
    },
    "Mean": {"role": TStatisticDatumRole.arithmetic_mean_role.value, "unit": "RFU"},
    "Geometric Mean": {
        "role": TStatisticDatumRole.geometric_mean_role.value,
        "unit": "RFU",
    },
    "Percentile": {"role": TStatisticDatumRole.percentile_role.value, "unit": "RFU"},
    "SD": {
        "role": TStatisticDatumRole.standard_deviation_role.value,
        "unit": "(unitless)",
    },
    "MADExact": {
        "role": TStatisticDatumRole.median_absolute_deviation_percentile_role.value,
        "unit": "(unitless)",
    },
    "Robust SD": {
        "role": TStatisticDatumRole.robust_standard_deviation_role.value,
        "unit": "(unitless)",
    },
    "Median Abs Dev": {
        "role": TStatisticDatumRole.median_absolute_deviation_role.value,
        "unit": "(unitless)",
    },
    # Count statistics
    "fj.stat.freqofparent": {
        "role": TStatisticDatumRole.frequency_of_parent_role.value,
        "unit": "%",
    },
    "fj.stat.freqofgrandparent": {
        "role": TStatisticDatumRole.frequency_of_grandparent_role.value,
        "unit": "%",
    },
    "fj.stat.freqoftotal": {
        "role": TStatisticDatumRole.frequency_of_total_role.value,
        "unit": "%",
    },
}

# Identify statistics that belong to the "Count" feature
COUNT_FIELDS = [
    "fj.stat.freqofparent",
    "fj.stat.freqofgrandparent",
    "fj.stat.freqoftotal",
    "fj.stat.freqof",
]

FLUORESCENCE_FIELDS = [
    "Median",
    "CV",
    "Robust CV",
    "Mean",
    "Geometric Mean",
    "Percentile",
    "SD",
    "MADExact",
    "Robust SD",
    "Median Abs Dev",
]


class RegionType(Enum):
    RECTANGLE = "Rectangle"
    POLYGON = "Polygon"
    ELLIPSOID = "Ellipsoid"
    CURLY_QUAD = "CurlyQuad"


class VertexRole(Enum):
    FOCI = "foci"
    EDGE = "edge"
