from datetime import timedelta

from allotropy.allotrope.models.shared.definitions.custom import (
    TNullableQuantityValueGramPerLiter,
    TNullableQuantityValueMillimolePerLiter,
    TNullableQuantityValueUnitPerLiter,
)

# Measurements of a sample have different timestamps, typically spaced closely together (max diff observed - 9 min)
# Some result files have multiple sets of measurements, over multiple days.
# Measurements with a time difference greater than MAX_MEASUREMENT_TIME_GROUP_DIFFERENCE from the last
# measurement recorded will be put into separate groups.
MAX_MEASUREMENT_TIME_GROUP_DIFFERENCE = timedelta(hours=1)


MOLAR_CONCENTRATION_CLASSES: list[
    (
        type[TNullableQuantityValueMillimolePerLiter]
        | type[TNullableQuantityValueGramPerLiter]
        | type[TNullableQuantityValueUnitPerLiter]
    )
] = [
    TNullableQuantityValueMillimolePerLiter,
    TNullableQuantityValueGramPerLiter,
    TNullableQuantityValueUnitPerLiter,
]

MOLAR_CONCENTRATION_CLS_BY_UNIT = {cls.unit: cls for cls in MOLAR_CONCENTRATION_CLASSES}


INFO_HEADER = [
    "row type",
    "data processing time",
    "col3",
    "col4",
    "col5",
    "col6",
    "model number",
    "device serial number",
    "software version",
    "analyst",
]

DATA_HEADER = [
    "row type",
    "measurement time",
    "sample identifier",
    "batch identifier",
    "sample role type",
    "col6",
    "analyte name",
    "col8",
    "concentration unit",
    "flag",
    "concentration value",
    "col12",
    "col13",
]


ANALYTES_LOOKUP = {
    "AC2B": "acetate",
    "AC2D": "acetate",
    "AQB": "alanine-glutamine",
    "AQD": "alanine-glutamine",
    "AQQB": "alanine-glutamine corrected",
    "NH3LB": "ammonia",
    "NH3B": "ammonia",
    "NH3D": "ammonia",
    "ARAB": "arabinose",
    "ARAD": "arabinose",
    "ASNLB": "asparagine",
    "ASNHB": "asparagine",
    "ASNHD": "asparagine",
    "ASPB": "aspartate",
    "ASPD": "aspartate",
    "CA2B": "calcium",
    "CA2D": "calcium",
    "CHO2B": "cholesterol",
    "CHO2D": "cholesterol",
    "ETOHB": "ethanol",
    "ETOHD": "ethanol",
    "FORB": "formate",
    "FORD": "formate",
    "GAL2B": "galactose",
    "GAL2D": "galactose",
    "GLC2L": "glucose",
    "GLC2B": "glucose",
    "GLC2D": "glucose",
    "GLC3D": "glucose",
    "GLC3B": "glucose",
    "GLC3L": "glucose",
    "GLU2B": "glutamate",
    "GLU2D": "glutamate",
    "GLN2B": "glutamine",
    "GLN2D": "glutamine",
    "GLYB": "glycerol",
    "GLYD": "glycerol",
    "GLYE": "glycerol",
    "FABLA": "Ig Fab human",
    "FABLB": "Ig Fab human",
    "FABHB": "Ig Fab human",
    "FABHD": "Ig Fab human",
    "IGGLB": "IgG human",
    "IGGHB": "IgG human",
    "IGGHD": "IgG human",
    "MIGLB": "IgG mouse",
    "MIGHB": "IgG mouse",
    "MIGHD": "IgG mouse",
    "FE2B": "iron",
    "FE2D": "iron",
    "LAC2B": "lactate",
    "LAC2D": "lactate",
    "LDH2B": "ldh",
    "LDH2D": "ldh",
    "MG2L": "magnesium",
    "MG2B": "magnesium",
    "MG2D": "magnesium",
    "NO3L": "nitrate",
    "NO3B": "nitrate",
    "NO3D": "nitrate",
    "PHO2L": "phosphate",
    "PHO2B": "phosphate",
    "PHO2D": "phosphate",
    "KB": "potassium",
    "KD": "potassium",
    "PYRB": "pyruvate",
    "PYRD": "pyruvate",
    "NAB": "sodium",
    "NAD": "sodium",
    "SUCB": "sucrose",
    "SUCD": "sucrose",
    "SUGLB": "sucrose corrected",
    "SUGLD": "sucrose corrected",
    "TP2B": "total protein",
    "TP2D": "total protein",
    "TP2LB": "total protein",
    "ODB": "optical_density",
    "ODD": "optical_density",
    "OSM2B": "osmolality",
}

SAMPLE_ROLE_TYPES = {"SAM": "Sample"}

SOLUTION_ANALYZER = "solution-analyzer"
OPTICAL_DENSITY = "optical_density"
BELOW_TEST_RANGE = "< TEST RNG"
