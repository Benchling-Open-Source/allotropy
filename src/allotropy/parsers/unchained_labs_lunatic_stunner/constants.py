import re

from allotropy.allotrope.models.shared.definitions.units import UNITLESS

DEFAULT_DETECTION_TYPE = "Absorbance"
DYNAMIC_LIGHT_SCATTERING_DETECTION_TYPE = "Dynamic Light Scattering"
DEVICE_TYPE = "plate reader"
MODEL_NUMBER = "Lunatic"
PRODUCT_MANUFACTURER = "Unchained Labs"
SOFTWARE_NAME = "Lunatic and Stunner Analysis"

# Wavelength columns will be "A<3-digit number>" with an optional pathlength specification, e.g. 'A260' or 'A260 (10mm)'
WAVELENGTH_COLUMNS_RE = re.compile(r"(?i)^A(\d{3})(?:\s\((\d+)?mm\))?$")
NO_WAVELENGTH_COLUMN_ERROR_MSG = (
    "The file is required to include an absorbance measurement column (e.g. A280)"
)
INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG = (
    msg
) = "The wavelength_column should follow the pattern A### (ex. A260)."
NO_DATE_OR_TIME_ERROR_MSG = "Unable to parse timestamp from input data, expected a 'Date' and 'Time' column in data or a 'Date' in metadata section."
NO_DEVICE_IDENTIFIER_ERROR_MSG = "Unable to parse device identifier, expected an 'Instrument ID' column in data or 'Instrument' in metadata section."
NO_MEASUREMENT_IN_PLATE_ERROR_MSG = (
    "The plate data does not contain absorbance measurement for {}."
)

CALCULATED_DATA_LOOKUP = {
    "a260": [
        {
            "column": "a260 concentration (ng/ul)",
            "name": "Concentration",
            "feature": "absorbance",
            "unit": "ng/µL",
        },
        {
            "column": "concentration (ng/ul)",
            "name": "Concentration",
            "feature": "absorbance",
            "unit": "ng/µL",
        },
        {
            "column": "background (a260)",
            "name": "Background (A260)",
            "feature": "absorbance",
            "unit": "mAU",
        },
        {
            "column": "a260/a230",
            "name": "A260/A230",
            "feature": "absorbance",
            "unit": UNITLESS,
        },
        {
            "column": "a260/a280",
            "name": "A260/A280",
            "feature": "absorbance",
            "unit": UNITLESS,
        },
    ],
    "a280": [
        {
            "column": "concentration (mg/ml)",
            "name": "Concentration",
            "feature": "absorbance",
            "unit": "mg/mL",
        },
        {
            "column": "background (a280)",
            "name": "Background (A280)",
            "feature": "absorbance",
            "unit": "mAU",
        },
        {
            "column": "a260/a280",
            "name": "A260/A280",
            "feature": "absorbance",
            "unit": UNITLESS,
        },
        {
            "column": "e1%",
            "name": "E1%",
            "feature": "absorbance",
            "unit": UNITLESS,
        },
        # Dynamic Light Scattering related calculations
        {
            "column": "kc/r (mol/g)",
            "name": "KC/R (mol/g)",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "kd (ml/g)",
            "name": "kD (ml/g)",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "b22 (ml.mol/g^2)",
            "name": "B22",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "optical contrast constant k (m^2 mol kg^-2)",
            "name": "Optical contrast constant K",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "z ave. dia (nm)",
            "name": "Z Average Diameter",
            "feature": "dynamic light scattering",
            "unit": "nm",
        },
        {
            "column": "pdi",
            "name": "Polydispersity Index",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "sd dia (nm)",
            "name": "Diameter Standard Deviation",
            "feature": "dynamic light scattering",
            "unit": "nm",
        },
        {
            "column": "diffusion coefficient (um^2/s)",
            "name": "Diffusion coefficient",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "peak of interest mean dia (nm)",
            "name": "Peak of Interest Mean Diameter",
            "feature": "dynamic light scattering",
            "unit": "nm",
        },
        {
            "column": "peak of interest mode dia (nm)",
            "name": "Peak of Interest Mode Diameter",
            "feature": "dynamic light scattering",
            "unit": "nm",
        },
        {
            "column": "peak of interest est. mw (kda)",
            "name": "Peak of Interest Est. MW",
            "feature": "dynamic light scattering",
            "unit": "kDa",
        },
        {
            "column": "peak of interest intensity (%)",
            "name": "Peak of Interest Intensity",
            "feature": "dynamic light scattering",
            "unit": "%",
        },
        {
            "column": "peak of interest mass (%)",
            "name": "Peak of Interest Mass",
            "feature": "dynamic light scattering",
            "unit": "%",
        },
        {
            "column": "peak of interest diffusion coefficient (um^2/s)",
            "name": "Peak of Interest Diffusion coefficient",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "derived intensity (cps)",
            "name": "Derived intensity",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "rayleigh ratio r (cm^-1)",
            "name": "Rayleigh ratio R",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "kd goodness of fit",
            "name": "kD goodness of fit",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "b22 goodness of fit",
            "name": "B22 goodness of fit",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "viscosity at t (cp)",
            "name": "Viscosity at T (cP)",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "viscosity at 20°c (cp)",
            "name": "Viscosity at 20°C (cP)",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "ri at t",
            "name": "RI at T",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "ri at 20°c",
            "name": "RI at 20°C",
            "feature": "dynamic light scattering",
            "unit": UNITLESS,
        },
        {
            "column": "diameter @ c=0 (nm)",
            "name": "Diameter @ C=0",
            "feature": "dynamic light scattering",
            "unit": "nm",
        },
    ],
}
