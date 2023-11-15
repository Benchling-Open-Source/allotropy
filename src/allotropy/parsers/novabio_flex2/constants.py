from typing import Any, Union

from allotropy.allotrope.models.shared.definitions.custom import (
    TNullableQuantityValueCell,
    TNullableQuantityValueGramPerLiter,
    TNullableQuantityValueMicrometer,
    TNullableQuantityValueMillimeterOfMercury,
    TNullableQuantityValueMillimolePerLiter,
    TNullableQuantityValueMillionCellsPerMilliliter,
    TNullableQuantityValueMilliOsmolesPerKilogram,
    TNullableQuantityValueOpticalDensity,
    TNullableQuantityValuePercent,
    TNullableQuantityValuePH,
    TNullableQuantityValueTODO,
    TNullableQuantityValueUnitPerLiter,
)

FILENAME_REGEX = r"^SampleResults(?P<device_identifier>.*)?(?P<processing_time>\d{4}-\d{2}-\d{2}_\d{6})\.csv$"

INVALID_FILENAME_MESSAGE = (
    "{} is not valid. File name is expected to have format of SampleResultsYYYY-MM-DD_HHMMSS.csv "
    "or SampleResults<Analyzer ID>YYYY-MM-DD_HHMMSS.csv where <Analyzer ID> is defined in Settings"
)

MOLAR_CONCENTRATION_CLASSES = Union[
    TNullableQuantityValueMillimolePerLiter,
    TNullableQuantityValueGramPerLiter,
    TNullableQuantityValueUnitPerLiter,
]
ALL_MOLAR_CONCENTRATION_CLASSES: list[
    Union[
        type[TNullableQuantityValueMillimolePerLiter],
        type[TNullableQuantityValueGramPerLiter],
        type[TNullableQuantityValueUnitPerLiter],
    ]
] = [
    TNullableQuantityValueMillimolePerLiter,
    TNullableQuantityValueGramPerLiter,
    TNullableQuantityValueUnitPerLiter,
]
MOLAR_CONCENTRATION_CLS_BY_UNIT = {
    cls.unit: cls for cls in ALL_MOLAR_CONCENTRATION_CLASSES
}

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

PROPERTY_MAPPINGS: dict[str, dict[str, Any]] = {
    "pco2": {
        "col_name": "PCO2",
        "cls": TNullableQuantityValueMillimeterOfMercury,
    },
    "co2_saturation": {
        "col_name": "CO2 Saturation",
        "cls": TNullableQuantityValuePercent,
    },
    "po2": {
        "col_name": "PO2",
        "cls": TNullableQuantityValueMillimeterOfMercury,
    },
    "o2_saturation": {
        "col_name": "O2 Saturation",
        "cls": TNullableQuantityValuePercent,
    },
    "optical_density": {
        "col_name": "Optical Density",
        "cls": TNullableQuantityValueOpticalDensity,
    },
    "pH": {
        "col_name": "pH",
        "cls": TNullableQuantityValuePH,
    },
    "osmolality": {
        "col_name": "Osm",
        "cls": TNullableQuantityValueMilliOsmolesPerKilogram,
    },
    "viability__cell_counter_": {
        "col_name": "Viability",
        "cls": TNullableQuantityValuePercent,
    },
    "total_cell_density__cell_counter_": {
        "col_name": "Total Density",
        "cls": TNullableQuantityValueMillionCellsPerMilliliter,
    },
    "viable_cell_density__cell_counter_": {
        "col_name": "Viable Density",
        "cls": TNullableQuantityValueMillionCellsPerMilliliter,
    },
    "average_live_cell_diameter__cell_counter_": {
        "col_name": "Average Live Cell Diameter",
        "cls": TNullableQuantityValueMicrometer,
    },
    "average_total_cell_diameter__cell_counter_": {
        "col_name": "Average Total Cell Diameter",
        "cls": TNullableQuantityValueMicrometer,
    },
    "total_cell_diameter_distribution__cell_counter_": {
        "col_name": "Total Cell Diameter Distribution",
        "cls": TNullableQuantityValueTODO,
    },
    "viable_cell_count__cell_counter_": {
        "col_name": "Total Live Count",
        "cls": TNullableQuantityValueCell,
    },
    "total_cell_count__cell_counter_": {
        "col_name": "Total Cell Count",
        "cls": TNullableQuantityValueCell,
    },
}
