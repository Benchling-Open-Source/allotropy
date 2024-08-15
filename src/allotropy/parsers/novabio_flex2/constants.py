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

BLOOD_GAS_DETECTION_MAPPINGS = {
    "po2": "PO2",
    "pco2": "PCO2",
    "carbon_dioxide_saturation": "CO2 Saturation",
    "oxygen_saturation": "O2 Saturation",
}

PH_DETECTION_MAPPINGS = {
    "ph": "pH",
    "temperature": "Vessel Temperature (°C)",
}

OSMOLALITY_DETECTION_MAPPINGS = {
    "osmolality": "Osm",
}

CELL_COUNTER_MAPPINGS = {
    "viability": "Viability",
    "total_cell_density": "Total Density",
    "viable_cell_density": "Viable Density",
    "average_live_cell_diameter": "Average Live Cell Diameter",
    "total_cell_count": "Total Cell Count",
    "viable_cell_count": "Total Live Count",
}
