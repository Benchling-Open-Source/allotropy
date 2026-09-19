"""Constants file for Agilent OpenLab CDS Adapter"""

from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    SampleRoleType,
)

DISPLAY_NAME = "Agilent OpenLab CDS"
PRODUCT_MANUFACTURER = "Agilent"
SAMPLE_ROLE_TYPE = {
    "Blank": SampleRoleType.blank_role.value,
    "Sample": SampleRoleType.sample_role.value,
}

# Molar mass results OpenLab CDS reports per peak for size-exclusion (GPC) methods, mapped from the
# result set element name to the custom information key and its unit. No ASM schema has a
# molecular-weight concept, so these are reported as peak custom information.
#
# Only methods with a GPC calibration report them, so they are absent from result sets acquired with
# a plain LC method. Element names follow the report column labels, as the other peak results do
# (Area/AreaPercent/Height); confirm them against a GPC result set before relying on them.
PEAK_MOLAR_MASS_FIELDS = {
    "Mn": ("Mn", "g/mol"),
    "Mw": ("Mw", "g/mol"),
    "Mp": ("Mp", "g/mol"),
    "Mz": ("Mz", "g/mol"),
    "PD": ("polydispersity", "(unitless)"),
}
