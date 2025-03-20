MODEL_NUMBER = "Flex2"
SOFTWARE_NAME = "NovaBio Flex"
DEVICE_TYPE = "solution-analyzer"
PRODUCT_MANUFACTURER = "Nova Biomedical"

FILENAME_REGEX = r"^SampleResults(?P<device_identifier>.*)?(?P<processing_time>\d{4}-\d{2}-\d{2}_\d{6})\.csv$"

INVALID_FILENAME_MESSAGE = (
    "{} is not valid. File name is expected to have format of SampleResultsYYYY-MM-DD_HHMMSS.csv "
    "or SampleResults<Analyzer ID>YYYY-MM-DD_HHMMSS.csv where <Analyzer ID> is defined in Settings"
)

ANALYTE_MAPPINGS = {
    "NH4+": {
        "name": "ammonium",
        "unit": "mmol/L",
    },
    "HCO3": {
        "name": "bicarbonate",
        "unit": "mmol/L",
    },
    "Ca++": {
        "name": "calcium",
        "unit": "mmol/L",
    },
    "Gluc": {
        "name": "glucose",
        "unit": "g/L",
    },
    "Glu": {
        "name": "glutamate",
        "unit": "mmol/L",
    },
    "Gln": {
        "name": "glutamine",
        "unit": "mmol/L",
    },
    "Lac": {
        "name": "lactate",
        "unit": "g/L",
    },
    "K+": {
        "name": "potassium",
        "unit": "mmol/L",
    },
    "Na+": {
        "name": "sodium",
        "unit": "mmol/L",
    },
}

DETECTION_PROPERTY_MAPPING = {
    "metabolite-detection": ["analytes"],
    "blood-gas-detection": [
        "po2",
        "po2_unit",
        "pco2",
        "pco2_unit",
        "carbon_dioxide_saturation",
        "oxygen_saturation",
    ],
    "ph-detection": [
        "ph",
        "temperature",
    ],
    "osmolality-detection": ["osmolality"],
    "cell-counting": [
        "viability",
        "total_cell_density",
        "total_cell_density_unit",
        "viable_cell_density",
        "viable_cell_density_unit",
        "average_live_cell_diameter",
        "total_cell_count",
        "viable_cell_count",
        "cell_type_processing_method",
        "cell_density_dilution_factor",
    ],
}

DATA_PROCESSING_FIELDS = [
    "cell_type_processing_method",
    "cell_density_dilution_factor",
]
