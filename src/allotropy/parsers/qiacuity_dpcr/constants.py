CALCULATED_DATA_CONFIGS: list[dict[str, str]] = [
    {
        "name": "CI (95%)",
        "keys": "CI (95%)",
        "unit": "%",
        "feature": "Positive Partition Count",
    },
    {
        "name": "SD",
        "keys": "SD",
        "unit": "(unitless)",
        "feature": "Number Concentration",
    },
    {
        "name": "CV%",
        "keys": "CV%",
        "unit": "%",
        "feature": "Number Concentration (#/μL)",
    },
    {
        "name": "Mean Concentration",
        "keys": "Mean conc. [copies/μL]",
        "unit": "#/μL",
        "feature": "Mean Concentration (#/μL)",
    },
]

BRAND_NAME = "Qiacuity Digital PCR System"
PRODUCT_MANUFACTURER = "Qiagen"
SOFTWARE_NAME = "Qiacuity Software Suite"
DEVICE_TYPE = "dPCR"
DEVICE_IDENTIFIER = "Qiacuity dPCR"

SAMPLE_ROLE_TYPE_MAPPING = {
    "Sample": "Sample Role",
    "Control": "Control Sample Role",
    "Non Template Control": "Blank Role",
}
