"""Constants file for Agilent OpenLab CDS Adapter"""

from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    SampleRoleType,
)

DISPLAY_NAME = "Agilent OpenLab CDS"
PRODUCT_MANUFACTURER = "Agilent"
# OpenLab's sample type, set per row in the sequence table, mapped to the ASM sample role type.
# The raw value is also reported as sample custom information, since OpenLab allows types that have
# no ASM equivalent and an unmapped type would otherwise be dropped.
SAMPLE_ROLE_TYPE = {
    "Blank": SampleRoleType.blank_role.value,
    "Calibration": SampleRoleType.calibration_sample_role.value,
    "Control": SampleRoleType.control_sample_role.value,
    "Sample": SampleRoleType.sample_role.value,
}

# Name of the peak custom field holding the GPC/SEC add-in's molecular weight averages.
GPC_RESULTS_FIELD = "GPCResults"

# The molecular weight averages OpenLab reports for a peak, mapped from their tag in the
# GPCPeakResults document to the name and unit used in the peak custom information document.
# TODO(ASM gaps): we believe molecular weight averages should be introduced to ASM. ASM has no
# molecular weight concept at any level, so these can only be reported as custom information.
GPC_PEAK_RESULT_FIELDS = {
    "PeakMn": ("number average molecular weight", "g/mol"),
    "PeakMw": ("weight average molecular weight", "g/mol"),
    "PeakMz": ("z average molecular weight", "g/mol"),
    "PeakMzPlusOne": ("z plus one average molecular weight", "g/mol"),
    "PeakMv": ("viscosity average molecular weight", "g/mol"),
    "PeakMp": ("peak molecular weight", "g/mol"),
    "PeakPd": ("polydispersity index", "(unitless)"),
}

# Reported alongside the averages, e.g. "Success" or "PeakOutsideCalibrationLimits". Kept because
# the averages are only meaningful within the column calibration range.
GPC_RESULT_STATUS_FIELD = "GPCCalculationsPeakResult"
GPC_RESULT_STATUS_KEY = "molecular weight calculation result"
