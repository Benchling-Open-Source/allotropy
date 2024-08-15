from typing import Any

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCell,
    TQuantityValueDegreeCelsius,
    TQuantityValueGramPerLiter,
    TQuantityValueMicrometer,
    TQuantityValueMillimeterOfMercury,
    TQuantityValueMillimolePerLiter,
    TQuantityValueMillionCellsPerMilliliter,
    TQuantityValueMilliOsmolesPerKilogram,
    TQuantityValuePercent,
    TQuantityValuePH,
    TQuantityValueUnitPerLiter,
)

FILENAME_REGEX = r"^SampleResults(?P<device_identifier>.*)?(?P<processing_time>\d{4}-\d{2}-\d{2}_\d{6})\.csv$"

INVALID_FILENAME_MESSAGE = (
    "{} is not valid. File name is expected to have format of SampleResultsYYYY-MM-DD_HHMMSS.csv "
    "or SampleResults<Analyzer ID>YYYY-MM-DD_HHMMSS.csv where <Analyzer ID> is defined in Settings"
)

CONCENTRATION_CLASSES = (
    TQuantityValueMillimolePerLiter
    | TQuantityValueGramPerLiter
    | TQuantityValueUnitPerLiter
)
ALL_CONCENTRATION_CLASSES: list[
    (
        type[TQuantityValueMillimolePerLiter]
        | type[TQuantityValueGramPerLiter]
        | type[TQuantityValueUnitPerLiter]
    )
] = [
    TQuantityValueMillimolePerLiter,
    TQuantityValueGramPerLiter,
    TQuantityValueUnitPerLiter,
]
CONCENTRATION_CLS_BY_UNIT = {cls.unit: cls for cls in ALL_CONCENTRATION_CLASSES}

ANALYTE_MAPPINGS: dict[str, dict[str, str]] = {
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

BLOOD_GAS_DETECTION_MAPPINGS: dict[str, dict[str, Any]] = {
    "pO2": {
        "col_name": "PO2",
        "cls": TQuantityValueMillimeterOfMercury,
    },
    "pCO2": {
        "col_name": "PCO2",
        "cls": TQuantityValueMillimeterOfMercury,
    },
    "carbon_dioxide_saturation": {
        "col_name": "CO2 Saturation",
        "cls": TQuantityValuePercent,
    },
    "oxygen_saturation": {
        "col_name": "O2 Saturation",
        "cls": TQuantityValuePercent,
    },
}

PH_DETECTION_MAPPINGS: dict[str, dict[str, Any]] = {
    "pH": {
        "col_name": "pH",
        "cls": TQuantityValuePH,
    },
    "temperature": {
        "col_name": "Vessel Temperature (°C)",
        "cls": TQuantityValueDegreeCelsius,
    },
}

OSMOLALITY_DETECTION_MAPPINGS: dict[str, dict[str, Any]] = {
    "osmolality": {
        "col_name": "Osm",
        "cls": TQuantityValueMilliOsmolesPerKilogram,
    },
}

CELL_COUNTER_MAPPINGS = {
    "viability__cell_counter_": {
        "col_name": "Viability",
        "cls": TQuantityValuePercent,
    },
    "total_cell_density__cell_counter_": {
        "col_name": "Total Density",
        "cls": TQuantityValueMillionCellsPerMilliliter,
    },
    "viable_cell_density__cell_counter_": {
        "col_name": "Viable Density",
        "cls": TQuantityValueMillionCellsPerMilliliter,
    },
    "average_live_cell_diameter__cell_counter_": {
        "col_name": "Average Live Cell Diameter",
        "cls": TQuantityValueMicrometer,
    },
    "total_cell_count": {
        "col_name": "Total Cell Count",
        "cls": TQuantityValueCell,
    },
    "viable_cell_count": {
        "col_name": "Total Live Count",
        "cls": TQuantityValueCell,
    },
}
