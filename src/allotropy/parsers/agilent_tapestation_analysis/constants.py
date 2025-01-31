BRAND_NAME = "TapeStation"
DETECTION_TYPE = "fluorescence"
DEVICE_TYPE = "electrophoresis device"
PRODUCT_MANUFACTURER = "Agilent"
SOFTWARE_NAME = "TapeStation Analysis Software"

SCREEN_TAPE_MISMATCH_ERROR = (
    "Mismatch error: Connector expected Sample ScreenTapeIDs to be present in the ScreenTape metadata block, "
    "got Sample ScreenTapeID '{}', expecting one of {} from metadata block."
)

UNIT_CLASS_LOOKUP: dict[str, str] = {
    "nt": "#",
    "bp": "#",
    "kD": "kDa",
}
NON_CALCULATED_DATA_TAGS_SAMPLE = [
    "Comment",
    "Observations",
    "Peaks",
    "Regions",
    "ScreenTapeID",
    "WellNumber",
]
NON_CALCULATED_DATA_TAGS_PEAK = [
    "Area",
    "Comment",
    "FromMW",
    "Height",
    "Number",
    "Observations",
    "PercentIntegratedArea",
    "PercentOfTotal",
    "Size",
    "ToMW",
]
NON_CALCULATED_DATA_TAGS_REGION = [
    "From",
    "To",
    "Area",
    "PercentOfTotal",
    "Comment",
]
